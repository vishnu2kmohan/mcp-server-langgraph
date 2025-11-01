"""
QuickStart Preset

Minimal in-memory setup for rapid prototyping and learning.
No Docker, no authentication, no infrastructure needed.

Features:
- In-memory checkpointing (MemorySaver)
- Free LLM defaults (Gemini Flash)
- Simple agent creation
- FastAPI server ready
- < 2 minute setup time

Example:
    >>> from mcp_server_langgraph.presets import QuickStart
    >>> agent = QuickStart.create("My Agent", tools=["calculator"])
    >>> result = agent.chat("What is 2 + 2?")
    >>> print(result)
"""

from typing import Any, Dict, List, Literal, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field


class QuickStartConfig(BaseModel):
    """Configuration for QuickStart preset."""

    name: str = Field(description="Agent name")
    tools: List[str] = Field(default_factory=list, description="List of tool names to include")
    llm: Literal["gemini-flash", "gemini-pro", "claude-haiku", "gpt-5-mini"] = Field(
        default="gemini-flash", description="LLM model to use"
    )
    system_prompt: Optional[str] = Field(default=None, description="Custom system prompt")
    temperature: float = Field(default=0.7, description="LLM temperature (0.0-1.0)")


class QuickStartAgent:
    """
    Quick-start agent with in-memory storage.

    No authentication, no infrastructure required.
    Perfect for learning and rapid prototyping.
    """

    def __init__(self, config: QuickStartConfig):
        """
        Initialize quick-start agent.

        Args:
            config: QuickStart configuration
        """
        self.config = config
        self.checkpointer = MemorySaver()
        self._graph = None
        self._compiled_agent = None

    def _build_graph(self) -> StateGraph:
        """Build the agent graph with specified tools."""
        from typing import Annotated, TypedDict

        # Define agent state
        class AgentState(TypedDict):
            """State for quick-start agent."""

            messages: Annotated[List[str], "Conversation messages"]
            query: str
            response: str
            context: Dict[str, Any]

        # Create graph
        graph = StateGraph(AgentState)

        # Simple handler node
        def handle_query(state: AgentState) -> AgentState:
            """Handle user query."""
            query = state["query"]

            # Simple echo response for now
            # In production, this would use LLM + tools
            system_msg = self.config.system_prompt or f"You are {self.config.name}, a helpful AI assistant."
            response = f"{system_msg}\n\nQuery: {query}\n\n"
            response += "This is a quick-start agent. For full LLM integration, see production setup."

            state["response"] = response
            state["messages"].append(f"User: {query}")
            state["messages"].append(f"Agent: {response}")

            return state

        # Build graph
        graph.add_node("handle", handle_query)
        graph.set_entry_point("handle")
        graph.set_finish_point("handle")

        return graph

    def compile(self) -> Any:
        """
        Compile the agent graph.

        Returns:
            Compiled LangGraph application
        """
        if self._compiled_agent is None:
            self._graph = self._build_graph()
            self._compiled_agent = self._graph.compile(checkpointer=self.checkpointer)

        return self._compiled_agent

    def chat(self, query: str, thread_id: str = "default") -> str:
        """
        Chat with the agent.

        Args:
            query: User query
            thread_id: Thread ID for conversation history

        Returns:
            Agent response
        """
        agent = self.compile()

        result = agent.invoke(
            {"query": query, "messages": [], "response": "", "context": {}},
            config={"configurable": {"thread_id": thread_id}},
        )

        return result["response"]

    def stream_chat(self, query: str, thread_id: str = "default"):
        """
        Stream chat responses.

        Args:
            query: User query
            thread_id: Thread ID for conversation history

        Yields:
            Response chunks
        """
        agent = self.compile()

        for chunk in agent.stream(
            {"query": query, "messages": [], "response": "", "context": {}},
            config={"configurable": {"thread_id": thread_id}},
        ):
            yield chunk

    def get_history(self, thread_id: str = "default") -> List[str]:
        """
        Get conversation history.

        Args:
            thread_id: Thread ID

        Returns:
            List of messages
        """
        # In-memory checkpointer doesn't expose history directly
        # This is a simplified implementation
        return []


class QuickStart:
    """
    QuickStart preset for rapid agent development.

    No Docker, no auth, no infrastructure needed.
    Perfect for learning and prototyping.

    Example:
        >>> agent = QuickStart.create("Research Assistant")
        >>> result = agent.chat("What is LangGraph?")
        >>> print(result)
    """

    @staticmethod
    def create(
        name: str,
        tools: Optional[List[str]] = None,
        llm: Literal["gemini-flash", "gemini-pro", "claude-haiku", "gpt-5-mini"] = "gemini-flash",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> QuickStartAgent:
        """
        Create a quick-start agent.

        Args:
            name: Agent name
            tools: List of tools to include (e.g., ["search", "calculator"])
            llm: LLM model to use (default: gemini-flash for free tier)
            system_prompt: Custom system prompt
            temperature: LLM temperature (0.0-1.0)

        Returns:
            QuickStartAgent instance

        Example:
            >>> agent = QuickStart.create(
            ...     "Research Agent",
            ...     tools=["search"],
            ...     llm="gemini-flash"
            ... )
            >>> result = agent.chat("Tell me about LangGraph")
            >>> print(result)
        """
        config = QuickStartConfig(
            name=name,
            tools=tools or [],
            llm=llm,
            system_prompt=system_prompt,
            temperature=temperature,
        )

        return QuickStartAgent(config)

    @staticmethod
    def create_app(
        name: str,
        tools: Optional[List[str]] = None,
        llm: str = "gemini-flash",
        port: int = 8000,
    ):
        """
        Create a FastAPI app with the agent.

        Args:
            name: Agent name
            tools: List of tools
            llm: LLM model
            port: Port to run on

        Returns:
            FastAPI application

        Example:
            >>> app = QuickStart.create_app("My Agent")
            >>> # Run with: uvicorn app:app --reload
        """
        from fastapi import FastAPI

        app = FastAPI(title=f"{name} - QuickStart", version="1.0.0")

        agent = QuickStart.create(name, tools, llm)  # type: ignore

        @app.get("/")
        def root():
            """Health check."""
            return {
                "status": "healthy",
                "agent": name,
                "preset": "quickstart",
                "message": f"{name} is running! Try POST /chat with a query.",
            }

        @app.post("/chat")
        def chat(query: str, thread_id: str = "default"):
            """Chat with the agent."""
            response = agent.chat(query, thread_id)
            return {"query": query, "response": response, "thread_id": thread_id}

        @app.get("/health")
        def health():
            """Health check endpoint."""
            return {"status": "healthy", "preset": "quickstart"}

        return app
