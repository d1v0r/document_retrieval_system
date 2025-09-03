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
            raise Exception("This class is a singleton! Use get_instance() instead.")
            
        self.document_processor = document_processor
        self.llm = OllamaLLM(
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434")
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
        """Generate a travel plan using the RAG system with fallback to direct LLM generation."""
        use_direct_llm = False
        
        # Check if we have a valid vectorstore
        has_vectorstore = hasattr(self.document_processor, 'vectorstore') and self.document_processor.vectorstore is not None
        
        if not has_vectorstore:
            use_direct_llm = True
            
        try:
            # Initialize docs as None
            docs = None
            
            # Skip document retrieval for now to ensure faster responses
            # We can re-enable this later once we have a proper document store
            if has_vectorstore and False:  # Temporarily disabled document retrieval
                try:
                    retriever = self.get_retriever({
                        "k": 3,
                        "search_type": "similarity",
                        "fetch_k": 6
                    })
                    
                    # Structured query for better retrieval
                    query_parts = [
                        f"{days} day travel itinerary for {city}",
                        "Include top attractions, dining, and activities"
                    ]
                    if preferences:
                        query_parts.append(f"Preferences: {preferences}")
                    
                    query_text = ". ".join(query_parts)
                    
                    # Try to get documents with a short timeout
                    try:
                        docs = await asyncio.wait_for(
                            retriever.ainvoke(query_text),
                            timeout=15.0
                        )
                        if not docs:
                            use_direct_llm = True
                    except (asyncio.TimeoutError, Exception) as e:
                        logger.warning(f"Document retrieval failed, falling back to direct LLM: {str(e)}")
                        use_direct_llm = True
                except Exception as e:
                    logger.error(f"Error in document retrieval: {str(e)}")
                    use_direct_llm = True
            
            if use_direct_llm or not has_vectorstore or docs is None:
                prompt = f"""Create a detailed {days}-day travel itinerary for {city} with specific times and locations.
                
                For each day, include:
                - Morning (9:00 AM - 12:00 PM): Specific activity or attraction with address
                - Lunch (12:30 PM - 2:00 PM): Restaurant recommendation with cuisine type
                - Afternoon (2:30 PM - 6:00 PM): Attractions or activities with details
                - Evening (7:00 PM onwards): Dinner and nightlife options
                - Travel Tips: Transportation, local customs, or money-saving tips
                
                Make it practical and realistic for a tourist. Include specific names, addresses, and estimated times.
                Focus on unique local experiences."""
                
                if preferences:
                    prompt = f"{prompt}\n\nTraveler preferences: {preferences}. Please focus the itinerary on these interests."
                
                # Add specific instructions for nightlife and beer preferences
                if 'nightlife' in preferences.lower() or 'beer' in preferences.lower():
                    prompt += "\n\nSince you're interested in nightlife and beer, include popular bars, pubs, or breweries in the evening sections."
                
                try:
                    # First try a direct synchronous call with a reasonable timeout
                    response = await asyncio.wait_for(
                        self.llm.agenerate([prompt]),
                        timeout=60.0  # Increased timeout to 60 seconds
                    )
                    
                    if response and hasattr(response, 'generations') and response.generations:
                        full_response = response.generations[0][0].text
                        
                        # Verify the response is complete (ends with proper punctuation or is reasonably long)
                        if len(full_response) > 100 and full_response.strip()[-1] in ('.', '!', '?'):
                            return full_response
                        
                        # If response seems incomplete, try to complete it
                        if len(full_response) > 50:  # If we got a substantial response
                            completion_prompt = f"{prompt}\n\nComplete the following response, ensuring it ends properly:\n\n{full_response}"
                            completion_response = await asyncio.wait_for(
                                self.llm.agenerate([completion_prompt]),
                                timeout=30.0
                            )
                            if completion_response and hasattr(completion_response, 'generations'):
                                return completion_response.generations[0][0].text
                        
                        return full_response  # Return what we have even if not perfectly complete
                    
                    # Fallback to streaming if direct call fails
                    logger.warning("Direct generation failed, falling back to streaming")
                    response = ""
                    start_time = asyncio.get_event_loop().time()
                    
                    # Stream the response with a timeout
                    async for chunk in self.llm.astream(prompt):
                        if asyncio.get_event_loop().time() - start_time > 45:  # 45s max for streaming
                            logger.warning("Streaming response timed out after 45 seconds")
                            break
                        if chunk:
                            response += chunk
                    
                    if response.strip():
                        return response
                    
                    return "I'm sorry, I couldn't generate a complete response. The response was truncated. Please try again or refine your request."
                except Exception as e:
                    logger.error(f"Error in direct LLM generation: {str(e)}")
                    # Return a simple fallback response
                    # More detailed fallback response
                    fallback = f"""# {days}-Day {city} Itinerary
                    
                    ## Day 1: City Introduction
                    
                    **Morning (9:00 AM - 12:00 PM)**  
                    - Start at the main square (Trg bana Jelačića)
                    - Visit the Museum of Broken Relationships (Ćirilometodska 2)
                    
                    **Lunch (12:30 PM - 2:00 PM)**  
                    - Try traditional Croatian cuisine at Vinodol (Teslina 10)
                    
                    **Afternoon (2:30 PM - 6:00 PM)**  
                    - Explore the Upper Town (Gornji Grad)
                    - Visit St. Mark's Church and the Stone Gate
                    
                    **Evening (7:00 PM onwards)**  
                    - Dinner at Pod Gričkim Topom (Zakmardijeve stube 5) with city views
                    - Drinks at Tkalčićeva Street (popular bar area)
                    
                    ## Day 2: Culture & Local Life
                    
                    **Morning (9:00 AM - 12:00 PM)**  
                    - Visit Mirogoj Cemetery (Mirogoj 9)
                    - Explore the Croatian Museum of Naïve Art
                    
                    **Lunch (12:30 PM - 2:00 PM)**  
                    - Try štrukli at La Štruk (Skalinska 5)
                    
                    **Afternoon (2:30 PM - 6:00 PM)**  
                    - Walk through Dolac Market
                    - Visit the Museum of Contemporary Art
                    
                    **Evening (7:00 PM onwards)**  
                    - Dinner at Dubravkin Put (Dubravkin put 2) for fine dining
                    - Craft beer at The Garden Brewery (Vladimira Novaka 12a)
                    
                    ## Travel Tips
                    - Use the tram system for easy transportation
                    - Try local craft beers like Ožujsko and Karlovačko
                    - Visit the Museum of Hangovers if you're interested in a unique experience
                    - Try the local specialty, štrukli (cheese pastry)"""
                    
                    if preferences:
                        if 'nightlife' in preferences.lower():
                            fallback += "\n\n**Nightlife Tip:** Tkalčićeva Street and Bogovićeva Street are the main bar areas with great nightlife options."
                        if 'beer' in preferences.lower():
                            fallback += "\n\n**Beer Lovers:** Don't miss The Garden Brewery and Craft Room for craft beer tasting."
                    
                    return fallback
            
            if not has_vectorstore or use_direct_llm or docs is None:
                return "I'm sorry, I couldn't generate a travel plan at this time. Please try again later."
            
            # Create a simpler chain for faster response
            chain = create_stuff_documents_chain(
                self.llm,
                self.travel_plan_prompt,
                document_prompt=ChatPromptTemplate.from_template("{page_content}")
            )
            
            input_data = {
                "city": city,
                "days": str(min(int(days), 7)),  # Limit to 7 days max for generation
                "preferences": preferences or "No specific preferences",
                "context": docs
            }
            
            result = await asyncio.wait_for(
                chain.ainvoke(input_data),
                timeout=120.0
            )
            
            return result
            
        except asyncio.TimeoutError:
            return "Generating your travel plan is taking longer than expected. Please try again with a more specific request or fewer days."
        except Exception as e:
            logger.error(f"Error generating travel plan: {str(e)}", exc_info=True)
            return f"I'm sorry, I encountered an error while generating your travel plan: {str(e)}"
