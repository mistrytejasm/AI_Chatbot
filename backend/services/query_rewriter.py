from typing import List, Dict, Any, Optional
from core.dependencies import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

class QueryRewriter:
    def __init__(self):
        self.llm = get_llm()
    
    async def rewrite_query_with_context(
        self, 
        current_query: str, 
        conversation_history: List[Dict[str, str]],
        max_history_turns: int = 3
    ) -> str:
        """Rewrite user query to include conversation context"""
        
        if not conversation_history:
            return current_query
        
        # Limit history to recent turns
        recent_history = conversation_history[-max_history_turns:]
        
        # Build conversation context
        context_parts = []
        for turn in recent_history:
            if turn.get('user') and turn.get('assistant'):
                context_parts.append(f"User: {turn['user']}")
                context_parts.append(f"Assistant: {turn['assistant'][:200]}...")  # Truncate long responses
        
        context = "\n".join(context_parts)
        
        system_prompt = """Given the conversation history and a follow-up question, rewrite the follow-up question to be a standalone question that includes all necessary context.

Rules:
- Keep the original intent and language
- Replace pronouns (this, that, it, his, her) with specific references from context
- Include entity names and important details
- If the question is already standalone, return it unchanged
- Focus on maintaining context for document search

Conversation History:
{context}

Follow-up Question: {current_query}

Standalone Question:"""

        messages = [
            SystemMessage(content=system_prompt.format(
                context=context,
                current_query=current_query
            ))
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            rewritten_query = response.content.strip()
            
            print(f"🔄 Query rewritten: '{current_query}' → '{rewritten_query}'")
            return rewritten_query
        
        except Exception as e:
            print(f"❌ Query rewriting failed: {e}")
            return current_query