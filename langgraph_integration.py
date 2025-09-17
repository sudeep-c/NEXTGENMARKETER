# langgraph_integration.py
#fastapi_app.py will import langgraph_integration.manager. If the module is missing, the import will fail and break your API. Adding this file first prevents that.

#The manager is defensive: it lazy-loads the orchestrator graph and returns helpful fallback errors if something goes wrong.

#It returns _thread_id so the API / front-end can persist the thread id in the session.
# langgraph_integration.py
import uuid
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger("langgraph_integration")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(ch)

# Try to import your orchestrator build function. It should return the compiled graph
# (or a callable) after your earlier orchestrator patch that compiles with checkpointer/store.
try:
    from orchestrator import build_graph as build_orchestrator_graph
except Exception as e:
    logger.warning("Could not import orchestrator.build_graph at import-time: %s", e)
    build_orchestrator_graph = None

class GraphManager:
    def __init__(self):
        self.graph = None
        # Try eager load (best-effort), but keep it resilient
        if build_orchestrator_graph is not None:
            try:
                self.graph = build_orchestrator_graph()
                logger.info("Orchestrator graph loaded into GraphManager at init.")
            except Exception as e:
                logger.exception("Failed to build orchestrator graph at init: %s", e)
                self.graph = None
        else:
            logger.info("No build_orchestrator_graph available at init; will lazy-load on first invoke.")

    def new_thread(self) -> str:
        return str(uuid.uuid4())

    def ensure_graph(self):
        if self.graph is None:
            if build_orchestrator_graph is None:
                raise RuntimeError("No orchestrator.build_graph available to construct a graph.")
            try:
                self.graph = build_orchestrator_graph()
                logger.info("Orchestrator graph lazy-loaded.")
            except Exception as e:
                logger.exception("Failed to lazy-load orchestrator graph: %s", e)
                raise

    def invoke(self, thread_id: Optional[str], user_prompt: str) -> Dict[str, Any]:
        """
        Invoke the compiled graph with a small state payload.
        Returns a dict-like final state and always includes '_thread_id'.
        """
        if thread_id is None:
            thread_id = self.new_thread()

        # Ensure the graph is ready
        self.ensure_graph()

        # Build a minimal state the graph can consume. Your orchestrator nodes
        # can read 'user_prompt' and 'thread_id' from this state.
        state = {
            "user_prompt": user_prompt,
            "thread_id": thread_id,
        }

        if self.graph is None:
            logger.error("Graph is not available to invoke.")
            return {"error": "graph_not_available", "_thread_id": thread_id}

        # --- Minimal change: supply LangGraph checkpointer-required `config` with thread_id ---
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Try invoking with config first (required by graphs compiled with checkpointers)
            if hasattr(self.graph, "invoke"):
                try:
                    result = self.graph.invoke(state, config=config)
                except TypeError:
                    # fallback if compiled graph.invoke doesn't accept config arg
                    result = self.graph.invoke(state)
            elif hasattr(self.graph, "run"):
                try:
                    result = self.graph.run(state, config=config)
                except TypeError:
                    result = self.graph.run(state)
            else:
                # If compiled graph is callable and may accept config
                try:
                    result = self.graph(state, config=config)
                except TypeError:
                    result = self.graph(state)
        except Exception as e:
            logger.exception("Graph invocation raised an exception: %s", e)
            return {"error": "invoke_failed", "exception": str(e), "_thread_id": thread_id}

        # Normalize to dict and ensure thread_id is present
        if not isinstance(result, dict):
            result = {"result": result}
        result["_thread_id"] = thread_id
        return result

# Export a singleton manager for easy imports (e.g., `from langgraph_integration import manager`)
manager = GraphManager()
