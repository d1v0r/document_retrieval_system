import asyncio
import os
import logging

from langchain.chains.combine_documents.stuff import create_stuff_documents_chain
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

class RAGSystem:
    _instance = None
    
    def __init__(self, document_processor: DocumentProcessor):
        if RAGSystem._instance is not None:
            raise Exception("Use get_instance()")
            
        self.document_processor = document_processor
        self.llm = OllamaLLM(
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            base_url=os.getenv("OLLAMA_HOST", "http://ollama:11434"),
            temperature=0.7,
            top_p=0.9,
            num_ctx=4096,
            num_thread=4,
            timeout=120.0,
            num_predict=4000,
            repeat_penalty=1.1, 
            top_k=40 
        )
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert travel assistant that provides accurate and helpful information based on the provided context.
            
            Guidelines for responses:
            1. Always base your answers strictly on the provided context
            2. If the context doesn't contain enough information, say "I don't have enough information to answer that question."
            3. Be concise but thorough in your responses
            4. Use markdown formatting for better readability (headings, lists, bold/italic)
            5. If referring to specific places or facts, mention the source document when possible"""),
            ("human", """Answer the following question based only on the provided context:
            
            Context:
            {context}
            
            Question: {question}""")
        ])
        
        self.travel_plan_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert travel planner creating a detailed itinerary based on the provided context.
            
            Create a travel itinerary that includes:
            1. Daily schedule with specific times
            2. Key attractions and activities
            3. Recommended dining options
            4. Travel tips and local insights"""),
            ("human", """Create a {days}-day travel itinerary for {city} with these preferences: {preferences}
            
            Context:
            {context}""")
        ])
        
        RAGSystem._instance = self
    
    @classmethod
    def get_instance(cls, document_processor: DocumentProcessor = None):
        if cls._instance is None:
            if document_processor is None:
                raise ValueError("document_processor is required for first initialization")
            cls._instance = cls(document_processor)
        return cls._instance
    
    def get_retriever(self, search_kwargs=None):
        if not hasattr(self, 'document_processor') or not hasattr(self.document_processor, 'vectorstore') or self.document_processor.vectorstore is None:
            raise ValueError("Vector store not initialized. Please load or create a vector store first.")
        
        if search_kwargs is None:
            search_kwargs = {"k": 5, "search_type": "similarity"}
            
        return self.document_processor.vectorstore.as_retriever(search_kwargs=search_kwargs)
    
    def answer_question(self, question: str) -> str:
        if not hasattr(self.document_processor, 'vectorstore') or self.document_processor.vectorstore is None:
            return "I'm sorry, I couldn't find any information to answer your question. The document search system is not properly initialized."
            
        try:
            retriever = self.get_retriever({"k": 5})
            
            docs = retriever.get_relevant_documents(question)
            
            qa_chain = create_stuff_documents_chain(
                self.llm,
                self.prompt_template,
                document_prompt=ChatPromptTemplate.from_template("{page_content}")
            )
            
            result = qa_chain.invoke({
                "input": {"question": question},
                "context": "\n\n".join([doc.page_content for doc in docs])
            })
            return result
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}", exc_info=True)
            return f"I'm sorry, I encountered an error while processing your question: {str(e)}"
    
    async def generate_travel_plan(self, city: str, days: int, preferences: str = None) -> str:
        try:
            days = min(int(days), 7)
            
            has_vectorstore = hasattr(self.document_processor, 'vectorstore') and self.document_processor.vectorstore is not None
            use_direct_llm = False
            docs = None
            
            if has_vectorstore:
                try:
                    if hasattr(self.document_processor.vectorstore, 'index') and hasattr(self.document_processor.vectorstore.index, 'ntotal') and self.document_processor.vectorstore.index.ntotal == 0:
                        logger.warning("Vector store is empty, attempting to process uploaded documents")
                        try:
                            uploads_dir = Path("uploads")
                            if uploads_dir.exists() and any(uploads_dir.iterdir()):
                                file_list = [str(f) for f in uploads_dir.glob('*') if f.is_file() and f.suffix.lower() in ['.pdf', '.txt', '.md']]
                                if file_list:
                                    logger.info(f"Found {len(file_list)} supported files in uploads directory, processing...")
                                    self.document_processor.load_or_create_vector_store(file_list)
                                    logger.info("Successfully processed uploaded documents")
                                else:
                                    logger.warning("No supported document files found in uploads directory")
                                    use_direct_llm = True
                            else:
                                logger.warning("No uploads directory found or it's empty")
                                use_direct_llm = True
                        except Exception as e:
                            logger.error(f"Error processing uploaded documents: {str(e)}", exc_info=True)
                            use_direct_llm = True
                    
                    if not use_direct_llm:
                        try:
                            docs = self.document_processor.vectorstore.similarity_search(
                                f"{city} travel guide {preferences or ''}",
                                k=5
                            )
                            if not docs:
                                logger.warning("No relevant documents found in vector store, falling back to direct LLM")
                                use_direct_llm = True
                        except Exception as e:
                            logger.warning(f"Error in similarity search: {str(e)}")
                            use_direct_llm = True

                except Exception as e:
                    logger.warning(f"Error querying vector store: {str(e)}", exc_info=True)
                    use_direct_llm = True

            if has_vectorstore and not use_direct_llm and docs:
                try:
                    chain = create_stuff_documents_chain(
                        self.llm,
                        self.travel_plan_prompt,
                        document_prompt=ChatPromptTemplate.from_template("{page_content}")
                    )
                    
                    input_data = {
                        "city": city,
                        "days": str(days),
                        "preferences": preferences or "No specific preferences",
                        "context": docs
                    }
                    
                    result = await asyncio.wait_for(
                        chain.ainvoke(input_data),
                        timeout=300.0 
                    )
                    
                    return result
                except asyncio.TimeoutError:
                    return "Generating your travel plan is taking longer than expected. Please try again with a more specific request or fewer days."
                except Exception as e:
                    logger.error(f"Error in document-based generation: {str(e)}", exc_info=True)
                    use_direct_llm = True

            if use_direct_llm or not has_vectorstore or not docs:
                prompt = f"""Create a detailed {days}-day travel itinerary for {city}.

For each day, include:
- Morning activities (9 AM - 12 PM)
- Lunch options
- Afternoon activities (2 PM - 6 PM)
- Dinner options
- Evening activities (if any)

Include practical information like:
- Opening hours for attractions
- Travel times between locations
- Estimated time spent at each location
- Any entrance fees or reservations needed
- Any other useful tips

Include specific names, addresses, and estimated times for all activities and locations."""
                
                if preferences:
                    prompt = f"{prompt}\n\nTraveler preferences: {preferences}. Please focus the itinerary on these interests."
                
                if preferences and ('nightlife' in preferences.lower() or 'beer' in preferences.lower()):
                    prompt += "\n\nSince you're interested in nightlife and beer, include popular bars, pubs, or breweries in the evening sections."
                
                try:
                    response = await asyncio.wait_for(
                        self.llm.agenerate([prompt]),
                        timeout=180.0  # Increased from 120 to 180 seconds
                    )
                    
                    if response and hasattr(response, 'generations') and response.generations:
                        full_response = response.generations[0][0].text
                        
                        if len(full_response) > 100 and full_response.strip()[-1] in ('.', '!', '?'):
                            return full_response
                        
                        if len(full_response) > 50:
                            completion_prompt = f"{prompt}\n\nComplete the following response, ensuring it ends properly:\n\n{full_response}"
                            completion_response = await asyncio.wait_for(
                                self.llm.agenerate([completion_prompt]),
                                timeout=60.0
                            )
                            if completion_response and hasattr(completion_response, 'generations'):
                                return completion_response.generations[0][0].text
                        
                        return full_response
                    
                    logger.warning("Direct generation failed, falling back to streaming")
                    response = ""
                    start_time = asyncio.get_event_loop().time()
                    
                    async for chunk in self.llm.astream(prompt):
                        if asyncio.get_event_loop().time() - start_time > 90:  # Increased from 45 to 90 seconds
                            logger.warning("Streaming response timed out after 90 seconds")
                            break
                        if chunk:
                            response += chunk
                    
                    if response.strip():
                        return response
                    
                    return "I'm sorry, I couldn't generate a complete response. Please try again or refine your request."
                except Exception as e:
                    logger.error(f"Error in direct LLM generation: {str(e)}")
                    return f"I apologize, but I encountered an error while generating your travel itinerary. Please try again later. Error: {str(e)[:200]}"

            return "I'm sorry, but I couldn't generate a travel plan at this time. Please try again later or upload relevant travel documents first."

        except Exception as e:
            logger.error(f"Error generating travel plan: {str(e)}", exc_info=True)
            return f"I'm sorry, I encountered an error while generating your travel plan: {str(e)}"
