set -e

ollama serve &

sleep 10

echo "Pulling model: $OLLAMA_MODEL"
ollama pull $OLLAMA_MODEL

wait $!
