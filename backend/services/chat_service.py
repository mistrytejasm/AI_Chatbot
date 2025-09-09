from typing import TypedDict, Annotated, Optional, AsyncGenerator, List, Dict, Any
from langgraph.graph import add_messages, StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from uuid import uuid4
import json
from core.dependencies import get_llm, memory
from services.controlled_search_service import ControlledSearchService
from utils.formatters import ResponseFormatter

class State(TypedDict):
    messages: Annotated[list, add_messages]

class ChatService:
    def __init__(self):
        self.llm = get_llm()
        self.controlled_search = ControlledSearchService()
        self.formatter = ResponseFormatter()
        self.graph = self._build_graph()

    def _get_system_prompt(self) -> str:
        """Enhanced system prompt for current information"""
        return """# Perplexity 2.0 - Advanced Research Assistant
 
You are an advanced AI research assistant with access to both web search and user-uploaded documents. Provide clear, comprehensive, and accurate answers with the following style:
 
## Response Format:
* Use **headers (##)** for major sections
* Use **bullet points (•)** for lists of items or features  
* Use **numbered lists** for step-by-step explanations
* Use **tables only** when comparing multiple items with specific attributes
* Write in **natural, conversational paragraphs** for explanations
* Start with a **brief overview** if the topic is complex
* Include **context, background, and synthesized insights** from reliable sources
* Be **concise but thorough**, explaining complex topics accessibly
* End with a **summary or key takeaways** for longer responses
* Maintain a **conversational yet professional tone**
 
## Source Priority:
Do NOT include citation markers like 【1†source】 or [1] in your response
1. **First check uploaded documents** for relevant information
2. **Then use web search** for additional context or current information
3. **Clearly distinguish** between document-sourced and web-sourced information
4. **Cite sources appropriately** - mention document names for document content
 
## When Documents are Available:
- **Always check documents first** before web searching
- **Prioritize document content** when it directly answers the question
- **Use web search to supplement** document information when helpful
- **Clearly indicate** when information comes from uploaded documents vs. web sources
 
Your role is to act as an **intelligent analyst**, offering insights, synthesis, and clear knowledge delivery from both uploaded documents and web sources.
"""

    async def search_documents_with_context(
    self, 
    query: str, 
    conversation_history: List[Dict[str, str]] = None,
    document_ids: Optional[List[str]] = None, 
    max_results: int = 5
    ) -> Dict[str, Any]:
        """Search documents with enhanced debugging"""
        try:
            # Rewrite query if we have conversation history
            if conversation_history:
                enhanced_query = await self.query_rewriter.rewrite_query_with_context(
                    query, conversation_history
                )
            else:
                enhanced_query = query
            
            print(f"🔍 RAG: Searching with query: '{enhanced_query}'")
            
            # Get available documents if none specified
            if not document_ids:
                available_docs = self.vector_store.list_stored_documents()
                if not available_docs:
                    print("❌ RAG: No documents available in vector store")
                    return {
                        "success": False,
                        "error": "No documents available for search",
                        "results": []
                    }
                document_ids = [doc["document_id"] for doc in available_docs]
                print(f"📚 RAG: Searching across {len(document_ids)} documents")
            
            # Search similar chunks with enhanced query
            print(f"🔍 RAG: Calling vector_store.search_similar_chunks...")
            results = await self.vector_store.search_similar_chunks(
                query=enhanced_query,
                document_ids=document_ids,
                max_results=max_results
            )
            
            print(f"📝 RAG: Vector search returned {len(results) if results else 0} results")
            
            if not results:
                print("❌ RAG: No relevant content found in vector search")
                return {
                    "success": False,
                    "error": "No relevant content found in documents",
                    "results": [],
                    "enhanced_query": enhanced_query
                }
            
            # Format results for RAG
            formatted_results = []
            for i, result in enumerate(results):
                if isinstance(result, dict):
                    formatted_chunk = {
                        "chunk_id": result.get("chunk_id", f"chunk_{i}"),
                        "content": result.get("content", ""),
                        "similarity_score": result.get("similarity_score", 0),
                        "source": result.get("metadata", {}).get("filename", "Unknown"),
                        "page": result.get("metadata", {}).get("pages", "N/A"),
                        "chunk_index": result.get("metadata", {}).get("chunk_index", i)
                    }
                    formatted_results.append(formatted_chunk)
                    print(f"✅ RAG: Formatted result {i+1}: {formatted_chunk['source']} (score: {formatted_chunk['similarity_score']:.3f})")
            
            print(f"✅ RAG: Found {len(formatted_results)} relevant chunks")
            
            return {
                "success": True,
                "query": query,
                "enhanced_query": enhanced_query,
                "results": formatted_results,
                "total_results": len(formatted_results)
            }
        
        except Exception as e:
            print(f"❌ RAG: Error searching documents: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "enhanced_query": query
            }


    def _extract_conversation_history(self, messages: List) -> List[Dict[str, str]]:
        """Extract conversation history for context"""
        history = []
        current_pair = {}
        
        for msg in reversed(messages):
            if hasattr(msg, 'content') and msg.content:
                if isinstance(msg, HumanMessage):
                    current_pair['user'] = msg.content
                elif isinstance(msg, AIMessage):
                    content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                    current_pair['assistant'] = content
                    
                    if 'user' in current_pair:
                        history.append(current_pair.copy())
                        current_pair = {}
                        
                        if len(history) >= 2:
                            break
        
        return list(reversed(history))

    async def _search_and_respond_node(self, state: State):
        """Enhanced search node with proper source extraction"""
        try:
            messages = state["messages"]
            user_message = messages[-1].content
            conversation_history = self._extract_conversation_history(messages[:-1])
            
            print(f"🔍 Processing controlled search for: '{user_message}'")
            
            # Perform enhanced controlled search
            search_results = await self.controlled_search.search_with_decomposition(
                user_query=user_message,
                conversation_history=conversation_history
            )
            
            if search_results["success"]:
                formatted_context = self.controlled_search.format_search_results(search_results)
                
                # Generate response
                system_msg = SystemMessage(content=self._get_system_prompt())
                context_msg = HumanMessage(content=formatted_context)
                response = await self.llm.ainvoke([system_msg, context_msg])
                
                # ENHANCED: Proper source extraction with debugging
                web_sources = []
                doc_sources = []
                seen_web_domains = set()
                seen_doc_sources = set()
                
                print(f"🔍 Processing search results for metadata:")
                print(f"   Web results: {len(search_results.get('web_results', []))}")
                print(f"   Doc results: {len(search_results.get('document_results', []))}")
                
                # Extract unique web sources
                for idx, result in enumerate(search_results.get("web_results", [])):
                    if isinstance(result, dict):
                        domain = result.get("source", "unknown")
                        title = result.get("title", "Unknown")
                        url = result.get("url", "")
                        
                        print(f"   Web {idx+1}: domain='{domain}', title='{title[:30]}...', url='{url[:30]}...'")
                        
                        if domain not in seen_web_domains and domain not in ["unknown", ""]:
                            web_sources.append({
                                "title": title,
                                "url": url,
                                "domain": domain
                            })
                            seen_web_domains.add(domain)
                            print(f"   ✅ Added web source: {domain}")
                
                # Extract unique document sources
                for idx, result in enumerate(search_results.get("document_results", [])):
                    if isinstance(result, dict):
                        filename = result.get("source", "Unknown Document")
                        
                        print(f"   Doc {idx+1}: filename='{filename}'")
                        
                        if filename not in seen_doc_sources and filename not in ["Unknown Document", ""]:
                            doc_sources.append({
                                "filename": filename,
                                "type": "document"
                            })
                            seen_doc_sources.add(filename)
                            print(f"   ✅ Added doc source: {filename}")
                
                # Enhanced metadata for frontend
                response.search_metadata = {
                    "original_query": user_message,
                    "sub_queries": search_results.get("sub_queries", []),
                    "web_sources": web_sources,
                    "document_sources": doc_sources,
                    "search_type": search_results.get("search_type", "mixed"),
                    "total_sources": len(web_sources) + len(doc_sources)
                }
                
                print(f"✅ Final metadata: {len(web_sources)} web, {len(doc_sources)} docs")
                
                return {"messages": [response]}
            else:
                error_msg = AIMessage(content=f"I apologize, but I encountered an error while searching: {search_results.get('error', 'Unknown error')}")
                return {"messages": [error_msg]}
        
        except Exception as e:
            print(f"❌ Search and respond error: {e}")
            import traceback
            traceback.print_exc()
            error_msg = AIMessage(content=f"I apologize, but I encountered an error: {str(e)}")
            return {"messages": [error_msg]}


    def _build_graph(self):
        """Build simplified graph with single search-and-respond node"""
        graph_builder = StateGraph(State)
        graph_builder.add_node("search_and_respond", self._search_and_respond_node)
        graph_builder.set_entry_point("search_and_respond")
        graph_builder.add_edge("search_and_respond", END)
        
        print("🏗️ Built controlled search graph (no recursive tools)")
        return graph_builder.compile(checkpointer=memory)

    async def generate_response(self, message: str, checkpoint_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Generate streaming responses with enhanced frontend metadata"""
        try:
            print(f"🚀 Starting controlled search response for: '{message}'")
            
            if checkpoint_id is None:
                new_checkpoint_id = str(uuid4())
                config = {"configurable": {"thread_id": new_checkpoint_id}}
                yield f'data: {{"type": "checkpoint", "checkpoint_id": "{new_checkpoint_id}"}}\n\n'
            else:
                config = {"configurable": {"thread_id": checkpoint_id}}

            # Show search start with original query
            query_json = self.formatter.safe_json_dumps(message)
            yield f'data: {{"type": "search_start", "query": {query_json}, "source": "controlled"}}\n\n'

            # Process with controlled search
            async for chunk in self.graph.astream(
                {"messages": [HumanMessage(content=message)]},
                config=config
            ):
                for node_name, node_output in chunk.items():
                    print(f"🔄 Processing node: {node_name}")
                    
                    if "messages" in node_output:
                        for message_obj in node_output["messages"]:
                            if hasattr(message_obj, "content") and message_obj.content:
                                
                                if hasattr(message_obj, "search_metadata"):
                                    metadata = message_obj.search_metadata
                                    
                                    # Send detailed query information
                                    query_data = {
                                        "type": "query_breakdown",
                                        "original_query": metadata.get("original_query", message),
                                        "sub_queries": metadata.get("sub_queries", []),
                                        "source": "controlled"
                                    }
                                    yield f'data: {json.dumps(query_data)}\n\n'
                                    print(f"📋 Sent query breakdown: {len(metadata.get('sub_queries', []))} sub-queries")
                                    
                                    # FIXED: Extract sources from metadata correctly
                                    web_sources = metadata.get("web_sources", [])
                                    doc_sources = metadata.get("document_sources", [])
                                    
                                    # Process web results for sources
                                    for result in metadata.get("web_results", []):
                                        if isinstance(result, dict):
                                            title = result.get("title", "Unknown")
                                            url = result.get("url", "")
                                            if url:
                                                try:
                                                    domain = url.split("//")[1].split("/")[0].replace("www.", "")
                                                    web_sources.append({
                                                        "title": title,
                                                        "url": url,
                                                        "domain": domain
                                                    })
                                                except:
                                                    web_sources.append({
                                                        "title": title,
                                                        "url": url,
                                                        "domain": "unknown"
                                                    })
                                    
                                    # Process document results for sources
                                    for result in metadata.get("document_results", []):
                                        if isinstance(result, dict):
                                            source = result.get("source", "Unknown Document")
                                            doc_sources.append({
                                                "filename": source,
                                                "type": "document"
                                            })
                                    
                                    # Send source information for "Reading sources" display
                                    sources_data = {
                                        "type": "search_results",
                                        "web_sources": web_sources,
                                        "document_sources": doc_sources,
                                        "source": "controlled",
                                        "total_web_sources": len(web_sources),
                                        "total_document_sources": len(doc_sources)
                                    }
                                    yield f'data: {json.dumps(sources_data)}\n\n'
                                    print(f"📊 Sent source details: {len(web_sources)} web + {len(doc_sources)} docs")
                                
                                # Send final formatted response
                                formatted_content = self.formatter.format_response(message_obj.content)
                                content_json = self.formatter.safe_json_dumps(formatted_content)
                                yield f'data: {{"type": "content", "content": {content_json}}}\n\n'
                                print(f"📤 SENDING FINAL RESPONSE: {formatted_content[:100]}...")

            print("✅ Controlled search completed successfully")
            yield f'data: {{"type": "end"}}\n\n'

        except Exception as e:
            print(f"❌ Critical error in controlled search: {e}")
            error_json = self.formatter.safe_json_dumps(f"I apologize, but I encountered an error: {str(e)}")
            yield f'data: {{"type": "content", "content": {error_json}}}\n\n'
            yield f'data: {{"type": "end"}}\n\n'