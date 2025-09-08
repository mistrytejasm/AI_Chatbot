from typing import TypedDict, Annotated, Optional, AsyncGenerator
from langgraph.graph import add_messages, StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage, SystemMessage
from uuid import uuid4
import json
from core.dependencies import get_llm, memory
from services.search_service import SearchService
from utils.formatters import ResponseFormatter

# Note: There is lots of recursive tool call is happening need to fix this 

class State(TypedDict):
    messages: Annotated[list, add_messages]


class ChatService:
    def __init__(self):
        self.llm = get_llm()
        self.search_service = SearchService()
        self.formatter = ResponseFormatter()
        self.graph = self._build_graph()

    def _get_system_prompt(self) -> str:
        """Enhanced system prompt for Perplexity-like responses"""
        return """# Perplexity 2.0 - Research Assistant Prompt

You are, an advanced AI research assistant. Provide clear, comprehensive, and accurate answers with the following style:

* Use **headers (##)** for major sections
* Use **bullet points (•)** for lists of items or features
* Use **numbered lists** for step-by-step explanations
* Use **tables only** when comparing multiple items with specific attributes
* Write in **natural, conversational paragraphs** for explanations
* Start with a **brief overview** if the topic is complex
* Include **context, background, and synthesized insights** from reliable sources
* Be **concise but thorough**, explaining complex topics accessibly
* End with a **summary or key takeaways** for longer responses
* Maintain a **conversational yet professional tone**; show confidence in facts, note uncertainties when needed, and anticipate follow-up questions.

Your role is not just to retrieve information but to act as an **analyst**, offering insights, synthesis, and clear knowledge delivery.
"""

    async def _model_node(self, state: State):
        """Process user input and generate responses"""
        try:
            messages = state["messages"]

            # Add system prompt if not present
            if not any(isinstance(msg, SystemMessage) for msg in messages):
                system_msg = SystemMessage(content=self._get_system_prompt())
                full_messages = [system_msg] + messages
            else:
                full_messages = messages

            # Use LLM with tools
            llm_with_tools = self.llm.bind_tools([self.search_service.search_tool])
            result = await llm_with_tools.ainvoke(full_messages)

            return {"messages": [result]}

        except Exception as e:
            print(f"❌ Model error: {e}")
            error_msg = AIMessage(
                content=f"I apologize, but I encountered an error while processing your request: {str(e)}")
            return {"messages": [error_msg]}

    async def _tool_node(self, state: State):
        """Execute tool calls with improved error handling"""
        try:
            last_message = state["messages"][-1]
            
            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                print("⚠️  No tool calls found")
                return {"messages": []}
            
            tool_calls = last_message.tool_calls
            tool_messages = []
            
            print(f"🔧 Processing {len(tool_calls)} tool calls")
            
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]
                
                print(f"🔍 Executing: {tool_name}")
                
                if tool_name == "tavily_search":  # Updated tool name
                    search_result = await self.search_service.perform_search(
                        tool_args.get("query", "")
                    )
                    
                    if search_result["success"]:
                        # Convert result to string for ToolMessage
                        content = str(search_result["results"])
                        tool_message = ToolMessage(
                            content=content,
                            tool_call_id=tool_id,
                            name=tool_name
                        )
                        print(f"✅ Search successful")
                    else:
                        tool_message = ToolMessage(
                            content=f"Search failed: {search_result['error']}",
                            tool_call_id=tool_id,
                            name=tool_name
                        )
                        print(f"❌ Search failed: {search_result['error']}")
                    
                    tool_messages.append(tool_message)
            
            return {"messages": tool_messages}
            
        except Exception as e:
            print(f"❌ Tool node error: {e}")
            return {"messages": []}


    def _tools_router(self, state: State):
        """Fixed routing logic to prevent infinite loops"""
        last_message = state["messages"][-1]
        
        # Case 1: Tool execution completed - go back to model for final response  
        if isinstance(last_message, ToolMessage):
            return "model"
        
        # Case 2: AI message with pending tool calls - execute tools
        if (isinstance(last_message, AIMessage) and 
            hasattr(last_message, "tool_calls") and 
            last_message.tool_calls):
            return "tool_node"
        
        # Case 3: AI message without tool calls - conversation ends
        return END




    def _build_graph(self):
        """Build the conversation graph with proper flow control"""
        graph_builder = StateGraph(State)
        
        # Add nodes
        graph_builder.add_node("model", self._model_node)
        graph_builder.add_node("tool_node", self._tool_node)
        
        # Set entry point
        graph_builder.set_entry_point("model")
        
        # Add conditional routing from model
        graph_builder.add_conditional_edges("model", self._tools_router)
        
        # Always return to model after tool execution
        graph_builder.add_edge("tool_node", "model")
        
        return graph_builder.compile(checkpointer=memory)


    async def generate_response(self, message: str, checkpoint_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Generate streaming chat responses"""
        try:
            print(f"🚀 Starting chat response for: '{message}'")
            
            # Store URLs for citation mapping
            current_urls = []

            # Handle checkpoint
            if checkpoint_id is None:
                new_checkpoint_id = str(uuid4())
                config = {"configurable": {"thread_id": new_checkpoint_id}}
                yield f'data: {{"type": "checkpoint", "checkpoint_id": "{new_checkpoint_id}"}}\n\n'
            else:
                config = {"configurable": {"thread_id": checkpoint_id}}

            # Stream graph responses
            async for chunk in self.graph.astream(
                    {"messages": [HumanMessage(content=message)]},
                    config=config
            ):
                for node_name, node_output in chunk.items():
                    print(f"🔄 Processing node: {node_name}")

                    if "messages" in node_output:
                        for message_obj in node_output["messages"]:

                            if hasattr(message_obj, "content") and message_obj.content:
                                message_type = type(message_obj).__name__
                                print(f"🔍 Processing {message_type}: {message_obj.content[:50]}...")

                                if message_type == "AIMessage":
                                    # Check for active tool calls
                                    has_active_tool_calls = (
                                        hasattr(message_obj, "tool_calls") and
                                        message_obj.tool_calls and
                                        len(message_obj.tool_calls) > 0 and
                                        any(call.get("name") == "tavily_search" for call in message_obj.tool_calls)
                                    )

                                    if has_active_tool_calls:
                                        # Handle search start
                                        for tool_call in message_obj.tool_calls:
                                            if tool_call.get("name") == "tavily_search":
                                                search_query = tool_call.get("args", {}).get("query", "")
                                                query_json = self.formatter.safe_json_dumps(search_query)
                                                yield f'data: {{"type": "search_start", "query": {query_json}}}\n\n'
                                                print(f"🔍 Search started: {search_query}")
                                    else:
                                        # Final AI response - format it properly WITH CITATIONS
                                        formatted_content = self.formatter.format_response_with_citations(
                                            message_obj.content, current_urls
                                        )
                                        content_json = self.formatter.safe_json_dumps(formatted_content)
                                        urls_json = self.formatter.safe_json_dumps(current_urls)
                                        
                                        # Send both content and citation URLs
                                        yield f'data: {{"type": "content", "content": {content_json}, "citations": {urls_json}}}\n\n'
                                        print(f"📤 SENDING FINAL RESPONSE: {formatted_content[:100]}...")

                                elif message_type == "ToolMessage" and hasattr(message_obj, "name"):
                                    if message_obj.name == "tavily_search":
                                        print(f"🔧 Processing tool message: {message_obj.content[:100]}...")
                                        urls = self.formatter.extract_urls_from_search_results(message_obj.content)
                                        current_urls.extend(urls)  # Store URLs for citations
                                        print(f"🔗 Extracted {len(urls)} URLs: {urls}")
                                        urls_json = self.formatter.safe_json_dumps(urls)
                                        yield f'data: {{"type": "search_results", "urls": {urls_json}}}\n\n'
                                        print(f"📤 Sent search results with {len(urls)} URLs")

            print("✅ Graph stream completed")
            yield f'data: {{"type": "end"}}\n\n'

        except Exception as e:
            print(f"❌ Critical error: {e}")
            error_json = self.formatter.safe_json_dumps(f"I apologize, but I encountered an error: {str(e)}")
            yield f'data: {{"type": "content", "content": {error_json}}}\n\n'
            yield f'data: {{"type": "end"}}\n\n'
