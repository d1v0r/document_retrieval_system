# Travel Document Retrieval System

A web application that provides travel information based on user input of destination town and duration of stay. Built with FastAPI and modern web technologies.

## Features

- Input validation for town and duration
- Responsive design
- Ollama LLM
- ChromaDB
- PDF document processing

## Prerequisites

- Python 3.8+
- Ollama
- ChromaDB

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd document_retrieval_system
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements_minimal.txt
   ```

## Environment Setup

1. Create a `.env` file in the project root with the following variables:
   ```
   # Server
   APP_HOST=0.0.0.0
   APP_PORT=8000
   DEBUG=true
   
   # ChromaDB
   CHROMA_DB_PATH=./chroma_db
   COLLECTION_NAME=documents
   
   # Embeddings
   EMBEDDING_MODEL=all-MiniLM-L6-v2
   ```

## Running the Application

### Development Mode
1. Start the FastAPI development server:
   ```bash
   uvicorn main:app --reload
   ```
2. Access the web interface at: http://localhost:8000
3. API documentation (Swagger UI) is available at: http://localhost:8000/docs

### Using Docker
1. Build and start the containers:
   ```bash
   docker-compose up --build
   ```
2. The application will be available at: http://localhost:8000

### Travel Planning
- `POST /api/generate-itinerary` - Generate travel itinerary
  ```json
  {
    "city": "Tokyo",
    "days": 3,
    "preferences": "museums, parks, local food"
  }
  ```