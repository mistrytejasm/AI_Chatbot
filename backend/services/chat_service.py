from typing import TypedDict, Annotated, Optional, AsyncGenerator
from langgraph.graph import add_messages, StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage, SystemMessage
from uuid import uuid4
import json

from core.dependencies import get_llm, memory
from services.search_service import SearchService
from utils.formatters import ResponseFormatter


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
        return """You are Perplexity 2.0, an advanced AI research assistant that provides comprehensive, well-structured, and insightful responses. Your goal is to be helpful, accurate, and thorough.

**Response Guidelines:**

1. **Structure your responses clearly:**
   - Use headers (##) for main topics
   - Use subheaders (###) for subtopics  
   - Use bullet points (•) for lists and key points
   - Organize information logically from general to specific

2. **Content Quality:**
   - Provide comprehensive yet concise answers
   - Include relevant context and background information
   - Synthesize information from multiple sources when available
   - Explain complex topics in an accessible way

3. **When using search:**
   - Always search for current, accurate information when needed
   - Synthesize search results into a coherent response
   - Don't just repeat raw search data - analyze and present it meaningfully
   - Cite or reference information appropriately

4. **Formatting Standards:**
   - Start with a brief overview if the topic is complex
   - Use numbered lists for sequential information
   - Use bullet points for features, benefits, or key points
   - End with a summary or key takeaways for longer responses

5. **Tone and Style:**
   - Be conversational yet professional
   - Show confidence in well-established facts
   - Acknowledge uncertainty when appropriate
   - Be helpful and anticipate follow-up questions

Remember: You are not just an information retriever - you are an intelligent analyst who provides valuable insights and well-structured knowledge."""

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
        """Execute tool calls (searches)"""
        try:
            tool_calls = state["messages"][-1].tool_calls
            tool_messages = []

            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                if tool_name == "tavily_search_results_json":
                    search_result = await self.search_service.perform_search(tool_args.get("query", ""))

                    if search_result["success"]:
                        tool_message = ToolMessage(
                            content=str(search_result["results"]),
                            tool_call_id=tool_id,
                            name=tool_name
                        )
                    else:
                        tool_message = ToolMessage(
                            content=f"Search failed: {search_result['error']}",
                            tool_call_id=tool_id,
                            name=tool_name
                        )

                    tool_messages.append(tool_message)

            return {"messages": tool_messages}
        except Exception as e:
            print(f"❌ Tool node error: {e}")
            return {"messages": []}

    def _tools_router(self, state: State):
        """Route to tools if needed"""
        try:
            last_message = state["messages"][-1]
            has_tools = hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0
            return "tool_node" if has_tools else END
        except Exception:
            return END

    def _build_graph(self):
        """Build the conversation graph"""
        graph_builder = StateGraph(State)
        graph_builder.add_node("model", self._model_node)
        graph_builder.add_node("tool_node", self._tool_node)
        graph_builder.set_entry_point("model")
        graph_builder.add_conditional_edges("model", self._tools_router)
        graph_builder.add_edge("tool_node", "model")

        return graph_builder.compile(checkpointer=memory)

    async def generate_response(self, message: str, checkpoint_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Generate streaming chat responses"""
        try:
            print(f"🚀 Starting chat response for: '{message}'")

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
                                            any(call.get("name") for call in message_obj.tool_calls)
                                    )

                                    if has_active_tool_calls:
                                        # Handle search start
                                        for tool_call in message_obj.tool_calls:
                                            if tool_call.get("name") == "tavily_search_results_json":
                                                search_query = tool_call.get("args", {}).get("query", "")
                                                query_json = self.formatter.safe_json_dumps(search_query)
                                                yield f'data: {{"type": "search_start", "query": {query_json}}}\n\n'
                                                print(f"🔍 Search started: {search_query}")
                                    else:
                                        # Final AI response - format it properly
                                        formatted_content = self.formatter.format_response(message_obj.content)
                                        content_json = self.formatter.safe_json_dumps(formatted_content)
                                        yield f'data: {{"type": "content", "content": {content_json}}}\n\n'
                                        print(f"📤 SENDING FINAL RESPONSE: {formatted_content[:100]}...")

                                elif message_type == "ToolMessage" and hasattr(message_obj, "name"):
                                    if message_obj.name == "tavily_search_results_json":
                                        print(f"🔧 Processing tool message: {message_obj.content[:100]}...")
                                        urls = self.formatter.extract_urls_from_search_results(message_obj.content)
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
