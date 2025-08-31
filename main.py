from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from rag_system import get_rag_system
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Travel Planner",
    description="API for travel planning",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

for dir_name in ["static", "templates"]:
    Path(dir_name).mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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

@app.post("/api/ingest")
async def ingest_documents(path: str = Form(...)):
    try:
        rag = get_rag_system()
        result = rag.document_processor.add_documents(path)
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
            
        return result
        
    except Exception as e:
        logger.error(f"Error ingesting documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def query_documents(request: QueryRequest):
    try:
        rag = get_rag_system()
        return rag.query(
            question=request.question,
            chat_history=request.chat_history,
            filter_metadata=request.filter_metadata
        )
        
    except Exception as e:
        logger.error(f"Error querying documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Redirect root to travel-planner."""
    return RedirectResponse(url="/travel-planner")

@app.get("/travel-planner", response_class=HTMLResponse)
async def travel_planner_page(request: Request):
    """Render the travel planner interface."""
    return templates.TemplateResponse("travel_planner.html", {"request": request})

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.post("/api/generate-itinerary")
async def generate_itinerary(request: TravelPlanRequest):
    try:
        rag = get_rag_system()
        
        query = f"""Create a detailed {request.days}-day travel itinerary for {request.city}.
        Include the following for each day:
        1. Morning activities with specific times and locations
        2. Lunch recommendations
        3. Afternoon activities with specific times and locations
        4. Dinner recommendations
        5. Evening activities if applicable
        
        Also include sections for:
        - Accessibility information
        - Insider tips and hidden gems
        """
        
        if request.preferences:
            query += f"\n\nTraveler preferences: {request.preferences}"
        
        response = rag.query(
            question=query,
            chat_history=[],
            filter_metadata={"type": "travel_guide"}
        )
        
        return {
            "status": "success",
            "data": {
                "destination": request.city,
                "days": request.days,
                "answer": response["answer"],
                "sources": response["sources"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating itinerary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate itinerary: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
