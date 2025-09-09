from typing import List, Dict, Any
from core.dependencies import get_llm
from langchain_core.messages import SystemMessage

class QueryDecomposer:
    def __init__(self):
        self.llm = get_llm()
    
    async def decompose_query(self, user_query: str, max_subqueries: int = 3) -> List[str]:
        """Decompose user query into focused sub-queries"""
        
        # Simple queries don't need decomposition
        if len(user_query.split()) <= 3:
            print(f"🔍 Simple query, no decomposition needed: {user_query}")
            return [user_query]
        
        decomposition_prompt = f"""You are a query decomposition expert. Break down this complex question into 2-3 focused, searchable sub-queries.

Rules:
- Generate maximum {max_subqueries} sub-queries
- Each sub-query should be independent and searchable
- Focus on different aspects of the main question
- Keep queries concise and specific
- Return ONLY the sub-queries, one per line
- NO numbering, bullets, or extra text

Question: {user_query}

Sub-queries:"""

        try:
            response = await self.llm.ainvoke([SystemMessage(content=decomposition_prompt)])
            
            # Parse sub-queries from response
            sub_queries = []
            lines = response.content.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if line and len(line) > 5:  # Avoid very short queries
                    # Clean up any numbering or bullets
                    cleaned = line.replace('1.', '').replace('2.', '').replace('3.', '')
                    cleaned = cleaned.replace('-', '').replace('•', '').replace('*', '').strip()
                    if cleaned:
                        sub_queries.append(cleaned)
            
            # Limit to max_subqueries and ensure we have the original
            sub_queries = sub_queries[:max_subqueries]
            if not sub_queries or len(sub_queries) == 0:
                print(f"⚠️ No valid sub-queries generated, using original")
                sub_queries = [user_query]
            
            print(f"🔍 Decomposed '{user_query}' into {len(sub_queries)} sub-queries:")
            for i, sq in enumerate(sub_queries, 1):
                print(f"   {i}. {sq}")
            
            return sub_queries
            
        except Exception as e:
            print(f"❌ Query decomposition failed: {e}")
            return [user_query]  # Fallback to original query