import re
from typing import List, Dict, Any, Optional
from services.search_service import SearchService
from services.rag_service import RAGService
from services.query_decomposer import QueryDecomposer
import asyncio

class ControlledSearchService:
    def __init__(self):
        self.search_service = SearchService()
        self.rag_service = RAGService()
        self.query_decomposer = QueryDecomposer()
    
    def _is_document_only_query(self, query: str) -> bool:
        """Detect if query is about uploaded documents only"""
        document_keywords = [
            'this book', 'this document', 'this pdf', 'this file',
            'uploaded document', 'the document', 'the book',
            'first page', 'title of', 'introduction', 'content of',
            'what this', 'whats this', 'about this'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in document_keywords)
    
    def _is_current_info_query(self, query: str) -> bool:
        """Detect if query needs current/recent information"""
        current_keywords = [
            '2025', '2024', 'current', 'today', 'latest', 'recent',
            'now', 'currently', 'new', 'update', 'squad', 'team',
            'time in india', 'date'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in current_keywords)
    
    async def search_with_decomposition(
        self, 
        user_query: str, 
        conversation_history: List[Dict[str, str]] = None,
        prioritize_documents: bool = False,
        max_results_per_query: int = 5
    ) -> Dict[str, Any]:
        """Enhanced search with intelligent routing"""
        
        try:
            print(f"🔍 Analyzing query type: '{user_query}'")
            
            # Determine search strategy
            is_doc_only = self._is_document_only_query(user_query)
            is_current_info = self._is_current_info_query(user_query)
            
            if is_doc_only:
                print("📚 Document-only query detected - skipping decomposition")
                return await self._search_documents_direct(user_query, conversation_history)
            elif is_current_info:
                print("🌐 Current info query detected - prioritizing web search")
                return await self._search_with_web_focus(user_query, conversation_history, max_results_per_query)
            else:
                print("🔀 Mixed query - using decomposition")
                return await self._search_with_full_decomposition(user_query, conversation_history, max_results_per_query)
        
        except Exception as e:
            print(f"❌ Controlled search failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "original_query": user_query,
                "sub_queries": [user_query],
                "document_results": [],
                "web_results": []
            }
    
    async def _search_documents_direct(
        self, 
        user_query: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Direct document search without decomposition"""
        
        document_results = []
        available_docs = await self.rag_service.get_available_documents()
        
        if available_docs:
            print(f"📚 Searching {len(available_docs)} documents directly...")
            
            doc_result = await self.rag_service.search_documents_with_context(
                query=user_query,
                conversation_history=conversation_history,
                max_results=8  # More results for better answers
            )
            
            if doc_result.get("success") and doc_result.get("results"):
                # Get unique document sources
                seen_sources = set()
                for result in doc_result["results"]:
                    if isinstance(result, dict):
                        source = result.get("source", "Unknown Document")
                        if source not in seen_sources:
                            enhanced_doc = {
                                "content": result.get("content", ""),
                                "source": source,
                                "similarity_score": result.get("similarity_score", 0),
                                "chunk_id": result.get("chunk_id", ""),
                                "query_used": user_query
                            }
                            document_results.append(enhanced_doc)
                            seen_sources.add(source)
                            
                            # Limit to 5 unique sources
                            if len(document_results) >= 5:
                                break
                
                print(f"✅ Found content from {len(document_results)} unique documents")
        
        return {
            "success": True,
            "original_query": user_query,
            "sub_queries": [user_query],  # Single query, no decomposition
            "document_results": document_results,
            "web_results": [],
            "total_document_results": len(document_results),
            "total_web_results": 0,
            "search_type": "document_only"
        }
    
    async def _search_with_web_focus(
        self, 
        user_query: str, 
        conversation_history: List[Dict[str, str]] = None,
        max_results_per_query: int = 5
    ) -> Dict[str, Any]:
        """Web-focused search with decomposition"""
        
        # Step 1: Decompose for better web results
        sub_queries = await self.query_decomposer.decompose_query(user_query)
        print(f"🌐 Web-focused search with {len(sub_queries)} sub-queries")
        
        # Step 2: Enhanced web search
        web_results = await self._perform_web_search(sub_queries, max_results_per_query)
        
        # Step 3: Limited document search (supplementary)
        document_results = []
        available_docs = await self.rag_service.get_available_documents()
        if available_docs:
            doc_result = await self.rag_service.search_documents_with_context(
                query=user_query,
                conversation_history=conversation_history,
                max_results=3  # Limited for supplementary info
            )
            if doc_result.get("success") and doc_result.get("results"):
                document_results = doc_result["results"][:3]
        
        return {
            "success": True,
            "original_query": user_query,
            "sub_queries": sub_queries,
            "document_results": document_results,
            "web_results": web_results,
            "total_document_results": len(document_results),
            "total_web_results": len(web_results),
            "search_type": "web_focused"
        }
    
    async def _search_with_full_decomposition(
        self, 
        user_query: str, 
        conversation_history: List[Dict[str, str]] = None,
        max_results_per_query: int = 5
    ) -> Dict[str, Any]:
        """Full decomposition search for complex queries"""
        
        # Step 1: Decompose query
        sub_queries = await self.query_decomposer.decompose_query(user_query)
        print(f"🔀 Mixed search with {len(sub_queries)} sub-queries")
        
        # Step 2: Web search
        web_results = await self._perform_web_search(sub_queries, max_results_per_query)
        
        # Step 3: Document search
        document_results = []
        available_docs = await self.rag_service.get_available_documents()
        if available_docs:
            print(f"📚 Searching {len(available_docs)} documents...")
            
            for sub_query in sub_queries:
                doc_result = await self.rag_service.search_documents_with_context(
                    query=sub_query,
                    conversation_history=conversation_history,
                    max_results=3
                )
                if doc_result.get("success") and doc_result.get("results"):
                    document_results.extend(doc_result["results"][:2])  # Top 2 per query
        
        return {
            "success": True,
            "original_query": user_query,
            "sub_queries": sub_queries,
            "document_results": document_results,
            "web_results": web_results,
            "total_document_results": len(document_results),
            "total_web_results": len(web_results),
            "search_type": "mixed"
        }
    
    async def _perform_web_search(self, sub_queries: List[str], max_results_per_query: int) -> List[Dict]:
        """Enhanced web search with comprehensive debugging"""
        web_results = []
        
        for i, sub_query in enumerate(sub_queries):
            try:
                response = await self.search_service.perform_search(sub_query)
                print(f"🔍 DEBUG Query {i+1}: '{sub_query}'")
                print(f"🔍 DEBUG Response type: {type(response)}")
                print(f"🔍 DEBUG Response keys: {response.keys() if isinstance(response, dict) else 'N/A'}")
                
                if isinstance(response, dict) and response.get("success"):
                    # Try multiple extraction methods
                    raw_results = response.get("results", {})
                    
                    # Method 1: Direct list
                    if isinstance(raw_results, list):
                        items = raw_results
                    # Method 2: Nested in 'results'
                    elif isinstance(raw_results, dict) and 'results' in raw_results:
                        items = raw_results['results']
                    # Method 3: Use the 'answer' field as fallback
                    elif response.get('answer'):
                        items = [{
                            'title': f"Search Result: {sub_query}",
                            'content': response['answer'],
                            'url': '',
                            'source': 'search_engine'
                        }]
                    else:
                        items = []
                    
                    print(f"🔍 DEBUG Found {len(items)} items")
                    
                    # Process items
                    for j, item in enumerate(items[:max_results_per_query]):
                        if isinstance(item, dict):
                            title = item.get('title', f'Result {j+1}')
                            content = item.get('content', item.get('snippet', ''))
                            url = item.get('url', '')
                            
                            if content and len(content.strip()) > 20:
                                domain = 'search_result'
                                if url:
                                    try:
                                        domain = url.split('//')[1].split('/')[0].replace('www.', '')
                                    except:
                                        pass
                                
                                web_results.append({
                                    'title': title,
                                    'content': content[:500],
                                    'url': url,
                                    'source': domain,
                                    'query_used': sub_query
                                })
                                print(f"✅ Added result: {title[:50]}... from {domain}")
                            
            except Exception as e:
                print(f"❌ Search error for query {i+1}: {e}")
        
        print(f"🌐 Total web results: {len(web_results)}")
        return web_results


    def format_search_results(self, search_results: Dict[str, Any]) -> str:
        """Format search results for LLM consumption"""
        if not search_results.get("success"):
            return f"Search failed: {search_results.get('error', 'Unknown error')}"
        
        formatted_parts = [
            f"**Original Query:** {search_results['original_query']}",
            f"**Search Strategy:** {search_results.get('search_type', 'mixed')} search",
            ""
        ]
        
        # Add sub-queries info
        sub_queries = search_results.get("sub_queries", [])
        if len(sub_queries) > 1:
            formatted_parts.append("**Sub-queries analyzed:**")
            for i, query in enumerate(sub_queries, 1):
                formatted_parts.append(f"{i}. {query}")
            formatted_parts.append("")
        
        # Add web results
        web_results = search_results.get("web_results", [])
        if web_results:
            formatted_parts.append("**From Web Sources:**")
            for i, result in enumerate(web_results[:6], 1):  # Limit to top 6
                if isinstance(result, dict):
                    title = result.get("title", "Unknown Title")
                    content = result.get("content", "")[:400]  # Limit content
                    url = result.get("url", "")
                    source = result.get("source", "Unknown")
                    
                    formatted_parts.append(f"**{i}. {title}**")
                    formatted_parts.append(f"   {content}...")
                    formatted_parts.append(f"   *Source: {source}*")
                    if url:
                        formatted_parts.append(f"   *URL: {url}*")
                    formatted_parts.append("")
        
        # Add document results
        document_results = search_results.get("document_results", [])
        if document_results:
            formatted_parts.append("**From Uploaded Documents:**")
            for i, result in enumerate(document_results[:5], 1):  # Limit to top 5
                if isinstance(result, dict):
                    source = result.get("source", "Unknown Document")
                    content = result.get("content", "")[:400]  # Limit content
                    score = result.get("similarity_score", 0)
                    
                    formatted_parts.append(f"**{i}. Document: {source}**")
                    formatted_parts.append(f"   {content}...")
                    formatted_parts.append(f"   *Relevance Score: {score:.3f}*")
                    formatted_parts.append("")
        
        # Add instructions for the LLM
        formatted_parts.extend([
            "---",
            f"**TASK:** Provide a comprehensive answer to: **{search_results['original_query']}**",
            "",
            "**INSTRUCTIONS:**",
            "• Use the search results above as your primary information source",
            "• Prioritize the most recent and relevant information",
            "• If using web sources, mention the source website",
            "• If using document sources, mention the document name",
            "• Structure your response with clear headers and bullet points",
            "• Be factual and cite sources when possible"
        ])
        
        return "\n".join(formatted_parts)