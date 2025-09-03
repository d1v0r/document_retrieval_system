# Travel Document Retrieval System

A modern web application that generates personalized travel itineraries based on user input. Built with FastAPI, Ollama, and FAISS for efficient document retrieval and processing.
<img width="1800" height="1169" alt="Screenshot 2025-09-03 at 04 26 43" src="https://github.com/user-attachments/assets/b68a01c4-0ff5-45fa-a108-624ffdce0f4e" />

## Features

- Create detailed travel plans based on destination and duration
- Extract and process information from document (PDF)
- FAISS-powered semantic search for relevant travel information
- Works on desktop and mobile devices
- Download your travel itinerary as a PDF

## Tech Stack

- FastAPI (Python), Vanilla JavaScript, HTML5, CSS3, Ollama LLM, FAISS and Docker


## 📋 Prerequisites

- Docker 20.10.0 or higher
- Docker Compose 2.0.0 or higher
- Git (only for cloning the repo)

## 🚀 Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/d1v0r/document_retrieval_system.git
   cd document_retrieval_system
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env if you need to change default settings
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```
   This will start all required services in the background.

4. **Access the application**:
   - http://localhost:8001

5. **Initial Setup**:
   - On first run, the system will download the Ollama model
   - docker-compose logs -f
