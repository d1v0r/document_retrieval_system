import os
import logging
import os

from pathlib import Path
from typing import List
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    DirectoryLoader,
    UnstructuredMarkdownLoader,
    WebBaseLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document


logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, persist_directory: str = "faiss_db"):
        self.embeddings = OllamaEmbeddings(
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434")
        )
        self.persist_directory = persist_directory
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
    def _get_loader(self, file_path: Path):
        """Get appropriate loader based on file extension."""
        if file_path.suffix == '.pdf':
            return PyPDFLoader(str(file_path))
        elif file_path.suffix == '.txt':
            return TextLoader(str(file_path), autodetect_encoding=True)
        elif file_path.suffix == '.md':
            return UnstructuredMarkdownLoader(str(file_path))
        elif file_path.suffix in ['.html', '.htm']:
            return WebBaseLoader(str(file_path))
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load documents from file paths."""
        all_docs = []
        for file_path in file_paths:
            try:
                loader = self._get_loader(Path(file_path))
                docs = loader.load()
                all_docs.extend(docs)
                logger.info(f"Loaded {len(docs)} documents from {file_path}")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {str(e)}")
                continue
        return all_docs

    def process_documents(self, file_paths: List[str]) -> List[Document]:
        """Process documents by loading and splitting them into chunks."""
        docs = self.load_documents(file_paths)
        if not docs:
            return []
            
        # Split documents into chunks
        texts = self.text_splitter.split_documents(docs)
        logger.info(f"Split into {len(texts)} chunks of text")
        return texts

    def create_vector_store(self, documents: List[Document]):
        """Create a FAISS vector store from documents."""
        if not documents:
            raise ValueError("No documents provided to create vector store")
            
        self.vectorstore = FAISS.from_documents(
            documents=documents,
            embedding=self.embeddings
        )
        return self.vectorstore

    def load_or_create_vector_store(self, file_paths: List[str] = None):
        """Load existing vector store or create a new one if it doesn't exist."""
        try:
            if os.path.exists(self.persist_directory):
                self.vectorstore = FAISS.load_local(
                    self.persist_directory,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("Loaded existing vector store")
                return self.vectorstore
        except Exception as e:
            logger.warning(f"Could not load existing vector store: {str(e)}")
            
        if not file_paths:
            raise ValueError("No existing vector store found and no file paths provided to create one")
            
        documents = self.process_documents(file_paths)
        self.vectorstore = self.create_vector_store(documents)
        self.vectorstore.save_local(self.persist_directory)
        logger.info(f"Created new vector store with {len(documents)} documents")
        return self.vectorstore

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Search for similar documents."""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized. Call load_or_create_vector_store first.")
        return self.vectorstore.similarity_search(query, k=k)

    def as_retriever(self, **kwargs):
        """Get a retriever for the vector store."""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized. Call load_or_create_vector_store first.")
        return self.vectorstore.as_retriever(**kwargs)

    def get(self, *args, **kwargs):
        """Get documents from the vector store.
        
        This method provides access to the underlying vector store's get method.
        It can be used to retrieve documents by their IDs or to get all documents.
        """
        if not self.vectorstore:
            raise ValueError("Vector store not initialized. Call load_or_create_vector_store first.")
            
        # If the vector store has a get method, use it
        if hasattr(self.vectorstore, 'get') and callable(self.vectorstore.get):
            return self.vectorstore.get(*args, **kwargs)
            
        # Otherwise, implement a basic get using similarity search
        if 'ids' in kwargs:
            # If specific IDs are provided, try to get those documents
            docs = []
            for doc_id in kwargs['ids']:
                # This is a simplified implementation - actual implementation may vary
                # based on how your vector store handles document retrieval
                try:
                    # Try to get the document by ID
                    doc = self.vectorstore.docstore.search(doc_id)
                    if doc:
                        docs.append(doc)
                except Exception as e:
                    logger.warning(f"Error getting document with ID {doc_id}: {str(e)}")
            return {"documents": [d.page_content for d in docs], 
                   "metadatas": [d.metadata for d in docs]}
        
        # If no IDs provided, return all documents (be careful with large collections!)
        return {"documents": [], "metadatas": []}
