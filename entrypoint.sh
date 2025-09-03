#!/bin/bash
set -e

shutdown() {
  echo "BYe Bye..."
  exit 0
}

trap 'shutdown' SIGTERM

until curl -s http://ollama:11434 >/dev/null 2>&1; do
  echo "Waiting for Ollama..."
  sleep 5
done

MODEL=${OLLAMA_MODEL:-llama3}
echo "Checking if model '$MODEL' is available..."
if ! curl -s http://ollama:11434/api/tags | grep -q "$MODEL"; then
  echo "Model '$MODEL' not found. Pulling..."
  curl -X POST http://ollama:11434/api/pull -d "{\"name\": \"$MODEL\"}" || echo "Warning: Failed to pull model '$MODEL'. Continuing..."
else
  echo "Model '$MODEL' is already available."
fi

mkdir -p /app/faiss_db /app/uploads

echo "Starting app..."
exec uvicorn main:app --host 0.0.0.0 --port 5000 --reload
