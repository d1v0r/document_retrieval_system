import asyncio
import uvicorn
import logging
import os
import shutil
import uuid
import faiss

from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from rag_system import RAGSystem

from document_processor import DocumentProcessor
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Travel Planner",
    description="API for travel planning",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.max_upload_size = 100 * 1024 * 1024  # 100MB

for dir_name in ["static", "templates"]:
    Path(dir_name).mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class FileInfo(BaseModel):
    filename: str
    saved_as: str
    path: str
    size: int

class UploadResponse(BaseModel):
    status: str
    message: str
    files: List[FileInfo]
    chunks_processed: int

class TravelPlanRequest(BaseModel):
    city: str
    days: int
    preferences: Optional[str] = None

class DocumentUploadRequest(BaseModel):
    path: str

class QueryRequest(BaseModel):
    question: str
    chat_history: List[Dict[str, str]] = []
    filter_metadata: Optional[Dict[str, Any]] = None

class ItineraryRequest(BaseModel):
    destination: str
    duration: int
    preferences: Optional[str] = None

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FAISS_DIR = Path("faiss_db")
FAISS_DIR.mkdir(parents=True, exist_ok=True, mode=0o777)

document_processor = None
rag_system = None

def initialize_rag_system():
    global document_processor, rag_system
    try:
        if document_processor is None:
            document_processor = DocumentProcessor()
            logger.info("Document processor initialized")
            
        if rag_system is None:
            rag_system = RAGSystem.get_instance(document_processor)
            logger.info("RAG system initialized successfully")
            
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {str(e)}", exc_info=True)
        raise

initialize_rag_system()

try:
    document_processor.load_or_create_vector_store()
    logger.info("Loaded existing vector store")
except Exception as e:
    logger.warning(f"Could not load existing vector store: {str(e)}")
    try:
        default_docs = Path("datasets/20_newsgroups")
        if default_docs.exists():
            logger.info("Initializing vector store with default documents")
            document_processor.load_or_create_vector_store([str(default_docs)])
            logger.info("Successfully initialized vector store with default documents")
        else:
            logger.warning("No default documents found at 'datasets/20_newsgroups'. Please upload documents first.")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {str(e)}")
        try:
            from langchain.docstore.in_memory import InMemoryDocstore
            import numpy as np
            index = faiss.IndexFlatL2(1536)
            document_processor.vectorstore = FAISS(
                document_processor.embeddings.embed_query,
                index,
                InMemoryDocstore({}),
                {}
            )
            logger.info("Created empty in-memory vector store")
        except Exception as e:
            logger.error(f"Failed to create in-memory vector store: {str(e)}")

index = faiss.IndexFlatL2(128)

@app.post("/api/upload", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(..., description="List of files to upload")):
    global rag_system, document_processor
    logger.info(f"Received upload request with {len(files)} files")
    
    try:
        initialize_rag_system()
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize the document processing system")

    if not files:
        logger.error("No files were provided in the upload request")
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    saved_files_info = []
    file_paths = []
    valid_extensions = ['.pdf', '.txt', '.md', '.docx']
    max_file_size = 50 * 1024 * 1024

    try:
        for file in files:
            try:
                file_extension = Path(file.filename).suffix.lower()
                if file_extension not in valid_extensions:
                    logger.warning(f"Invalid file type: {file_extension} for file {file.filename}")
                    continue
                
                file_content = await file.read()
                file_size = len(file_content)
                
                if file_size > max_file_size:
                    logger.warning(f"File {file.filename} is too large: {file_size} bytes")
                    continue
                
                await file.seek(0)
                
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                file_path = UPLOAD_DIR / unique_filename
                
                with open(file_path, "wb") as buffer:
                    buffer.write(file_content)
                
                saved_files_info.append({
                    "filename": file.filename,
                    "saved_as": unique_filename,
                    "path": str(file_path),
                    "size": file_size
                })
                file_paths.append(str(file_path))
                logger.info(f"Successfully saved file: {file.filename} as {unique_filename}")
                
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}", exc_info=True)
                continue

        if not file_paths:
            logger.error("No valid files were processed after validation")
            raise HTTPException(status_code=400, detail="No valid files were processed. Please ensure files are PDF, TXT, MD, or DOCX and under 50MB.")

        logger.info(f"Processing {len(file_paths)} documents...")
        new_documents = document_processor.process_documents(file_paths)
        if not new_documents:
            raise HTTPException(status_code=400, detail="No content could be extracted from the uploaded files.")

        if document_processor.vectorstore:
            document_processor.vectorstore.add_documents(new_documents)
            logger.info(f"Added {len(new_documents)} new document chunks to the existing vector store.")
        else:
            document_processor.create_vector_store(new_documents)
            logger.info("Created new vector store with uploaded documents.")

        if document_processor.vectorstore:
            document_processor.vectorstore.save_local(FAISS_DIR)

        rag_system = RAGSystem.get_instance(document_processor)
        
        # Return a proper Pydantic model response
        return {
            "status": "success",
            "message": f"Successfully processed and indexed {len(saved_files_info)} files.",
            "files": saved_files_info,
            "chunks_processed": len(new_documents)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing files: {str(e)}", exc_info=True)
        for path in file_paths:
            if os.path.exists(path):
                os.unlink(path)
        raise HTTPException(status_code=500, detail=f"An error occurred while processing files: {str(e)}")
 
@app.post("/api/ingest", response_class=JSONResponse)
async def ingest_documents(path: str = Form(...)):
    try:
        if not os.path.exists(path):
            raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")
            
        document_processor.load_or_create_vector_store([path])
        
        vectors = document_processor.get_vectors([path])
        index.add(vectors)
        
        return {"status": "success", "message": f"Documents from {path} processed successfully"}
    except Exception as e:
        logger.error(f"Error ingesting documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query", response_class=JSONResponse)
async def query_documents(request: QueryRequest):
    try:
        if not hasattr(rag_system, 'vectorstore') or rag_system.vectorstore is None:
            raise HTTPException(status_code=400, detail="No documents have been loaded yet. Please upload some documents first.")
            
        try:
            answer = rag_system.answer_question(question=request.question)
            
            retriever = rag_system.get_retriever({"k": 5})
            docs = retriever.get_relevant_documents(request.question)
            
            results = [{
                "rank": i + 1,
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": doc.metadata.get('score', 0.0) if hasattr(doc, 'metadata') else 0.0
            } for i, doc in enumerate(docs)]
            
            return {
                "status": "success",
                "answer": answer,
                "documents": results,
                "query": request.question
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error processing your query: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/travel-planner")

@app.get("/travel-planner", response_class=HTMLResponse)
async def travel_planner_page(request: Request):
    return templates.TemplateResponse("travel_planner.html", {"request": request})

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": str(exc.detail)},
    )

@app.post("/api/generate-itinerary", response_class=JSONResponse)
async def generate_itinerary(request: ItineraryRequest):
    try:
        if rag_system is None:
            raise HTTPException(status_code=500, detail={"status": "error", "message": "RAG system not properly initialized"})
        
        duration = min(int(request.duration), 7)
        
        travel_plan = await rag_system.generate_travel_plan(
            city=request.destination,
            days=duration,
            preferences=request.preferences
        )
        
        return {
            "status": "success",
            "itinerary": travel_plan,
            "destination": request.destination,
            "duration": duration
        }
            
    except HTTPException as he:
        logger.error(f"HTTP error generating itinerary: {str(he.detail)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating itinerary: {str(e)}", exc_info=True)
        return {
            "status": "success",
            "itinerary": f"I'm having trouble generating a travel plan right now. Please try again later. Error: {str(e)[:100]}",
            "destination": request.destination,
            "duration": request.duration
        }

@app.get("/api/documents", response_class=JSONResponse)
async def list_documents():
    try:
        files = []
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
        
        return {
            "status": "success",
            "documents": files
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
