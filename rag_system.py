from typing import List, Dict, Any
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from document_processor import DocumentProcessor
import os
import logging

logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self, document_processor: DocumentProcessor):
        """Initialize the RAG system with a document processor."""
        self.document_processor = document_processor
        self.llm = OllamaLLM(
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434")
        )
        
        # Define the prompt template for the travel assistant
        self.prompt_template = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
        You are a knowledgeable and friendly travel assistant. Your task is to create accurate, 
        well-structured, detailed and engaging travel information based on the provided context.
        
        Guidelines:
        - Use the context below to answer the user's question.
        - If the context doesn't contain relevant information, say "I don't have enough information to answer that question."
        - Provide clear, well-structured responses with bullet points or numbered lists when appropriate.
        - Include interesting details and practical information from the context.
        - Be concise but thorough in your responses.
        - Highlight important names in bold.
        
        Context:
        {context}
        
        <|eot_id|><|start_header_id|>user<|end_header_id|>
        Question: {question}
        
        Please provide a helpful and informative response based on the context above.
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
        
        self.prompt_template = ChatPromptTemplate.from_template(self.prompt_template)
        
        self.qa_chain = self._create_qa_chain()
    
    def _create_qa_chain(self):
        return create_stuff_documents_chain(
            llm=self.llm,
            prompt=self.prompt_template
        )
    
    def query(self, question: str, chat_history: List[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        if chat_history is None:
            chat_history = []
            
        try:
            # Get relevant documents
            docs = self.document_processor.query_documents(question, k=5)  # Increased from 3 to 5 for more context
            
            if not docs:
                return {
                    "answer": "I couldn't find any relevant information to answer your question. Please try again!",
                    "sources": []
                }
            
            response = self.qa_chain.invoke({
                "context": docs,
                "question": question,
                "chat_history": chat_history
            })
            
            sources = []
            seen_sources = set()
            for doc in docs:
                source = doc.metadata.get("source", "Unknown")
                if source not in seen_sources:
                    seen_sources.add(source)
                    sources.append({
                        "source": source,
                        "score": 0.0,
                        "page_content": doc.page_content[:200] + "..."
                    })
            
            return {
                "answer": response,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {str(e)}", exc_info=True)
            return {
                "answer": "Sorry, I encountered an error while processing your request.",
                "sources": []
            }

_rag_system = None

def get_rag_system():
    global _rag_system
    if _rag_system is None:
        processor = DocumentProcessor()
        _rag_system = RAGSystem(processor)
    return _rag_system
