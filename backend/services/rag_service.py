from typing import List, Dict, Any, Optional
from services.vector_store import VectorStore
from services.search_service import SearchService
from services.query_rewriter import QueryRewriter  # NEW IMPORT
import json

class RAGService:
    def __init__(self):
        self.vector_store = VectorStore()
        self.search_service = SearchService()
        self.query_rewriter = QueryRewriter()  # NEW
    
    def refresh_vector_store(self):
        """Refresh vector store to pick up latest documents"""
        print("🔄 RAG: Refreshing vector store...")
        self.vector_store.refresh_client()

    async def search_documents_with_context(
        self, 
        query: str, 
        conversation_history: List[Dict[str, str]] = None,
        document_ids: Optional[List[str]] = None, 
        max_results: int = 5,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Search documents with conversation context"""
        try:

            # Optionally refresh vector store before search
            if force_refresh:
                self.refresh_vector_store()
                
            # Rewrite query if we have conversation history
            if conversation_history:
                enhanced_query = await self.query_rewriter.rewrite_query_with_context(
                    query, conversation_history
                )
            else:
                enhanced_query = query
            
            print(f"🔍 RAG: Searching with enhanced query: {enhanced_query[:100]}...")
            
            # Get available documents if none specified
            if not document_ids:
                available_docs = self.vector_store.list_stored_documents()
                if not available_docs:
                    return {
                        "success": False,
                        "error": "No documents available for search",
                        "results": []
                    }
                document_ids = [doc["document_id"] for doc in available_docs]
                print(f"📚 RAG: Searching across {len(document_ids)} documents")
            
            # Search similar chunks with enhanced query
            results = await self.vector_store.search_similar_chunks(
                query=enhanced_query,  # Use enhanced query
                document_ids=document_ids,
                max_results=max_results
            )
            
            if not results:
                return {
                    "success": False,
                    "error": "No relevant content found in documents",
                    "results": [],
                    "enhanced_query": enhanced_query
                }
            
            # Format results for RAG
            formatted_results = []
            for i, result in enumerate(results):
                formatted_chunk = {
                    "chunk_id": result["chunk_id"],
                    "content": result["content"],
                    "similarity_score": result["similarity_score"],
                    "source": result["metadata"].get("filename", "Unknown"),
                    "page": result["metadata"].get("pages", "N/A"),
                    "chunk_index": result["metadata"].get("chunk_index", i)
                }
                formatted_results.append(formatted_chunk)
            
            print(f"✅ RAG: Found {len(formatted_results)} relevant chunks with enhanced query")
            
            return {
                "success": True,
                "query": query,
                "enhanced_query": enhanced_query,
                "results": formatted_results,
                "total_results": len(formatted_results)
            }
        
        except Exception as e:
            print(f"❌ RAG: Error searching documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "enhanced_query": query
            }
    
    # Keep existing methods but add conversation_history parameter
    async def search_documents(self, query: str, document_ids: Optional[List[str]] = None, max_results: int = 5) -> Dict[str, Any]:
        """Backward compatibility - calls new method without conversation history"""
        return await self.search_documents_with_context(
            query=query, 
            conversation_history=None,
            document_ids=document_ids,
            max_results=max_results
        )
    
    def format_context_for_llm(self, search_results: List[Dict[str, Any]], query: str, enhanced_query: str = None) -> str:
        """Format search results into context for LLM"""
        if not search_results:
            return ""
        
        context_parts = [
            "Based on the uploaded documents, here is the relevant information:",
            ""
        ]
        
        if enhanced_query and enhanced_query != query:
            context_parts.extend([
                f"(Context-enhanced query: {enhanced_query})",
                ""
            ])
        
        for i, result in enumerate(search_results, 1):
            source_info = f"Source: {result['source']}"
            if result.get('page') and result['page'] != 'N/A':
                source_info += f" (Page {result['page']})"
            
            context_parts.extend([
                f"**Relevant Content {i}:** ({source_info})",
                result['content'],
                ""
            ])
        
        context_parts.extend([
            "---",
            f"Please answer the following question based on the above context: {query}",
            "",
            "If the answer is not fully contained in the provided context, you may supplement with your general knowledge, but clearly indicate what comes from the documents vs. your general knowledge."
        ])
        
        return "\n".join(context_parts)

    async def get_available_documents(self) -> List[Dict[str, Any]]:
        """Get list of available documents"""
        return self.vector_store.list_stored_documents()