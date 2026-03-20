"""
AVAE LangGraph pipeline (Task 3.1).

Graph: burst_pdf → classify_pages → extract_parallel → merge_extractions → normalize → fetch_api
       → verify → route_hitl → [persist | human_review → persist]
"""
import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from app.graph.checkpointer import get_checkpointer
from app.graph.state import AVAEState
from app.graph.nodes import (
    burst_pdf,
    classify_pages,
    extract_parallel,
    merge_extractions,
    normalize,
    fetch_api,
    verify,
    route_hitl,
    human_review,
    persist,
    handle_error,
)

logger = logging.getLogger(__name__)


def _route_hitl(state: AVAEState) -> Literal["persist", "human_review"]:
    """Route based on verification status."""
    return route_hitl(state)  # type: ignore


def _route_after_burst(state: AVAEState) -> Literal["classify_pages", "handle_error"]:
    """Route after burst_pdf: continue or handle error."""
    if state.get("error"):
        return "handle_error"
    return "classify_pages"


def build_avae_graph():
    """Build and compile the AVAE verification graph."""
    builder = StateGraph(AVAEState)

    # Nodes
    builder.add_node("burst_pdf", burst_pdf)
    builder.add_node("classify_pages", classify_pages)
    builder.add_node("extract_parallel", extract_parallel)
    builder.add_node("merge_extractions", merge_extractions)
    builder.add_node("normalize", normalize)
    builder.add_node("fetch_api", fetch_api)
    builder.add_node("verify", verify)
    builder.add_node("human_review", human_review)
    builder.add_node("persist", persist)
    builder.add_node("handle_error", handle_error)

    # Entry + conditional: burst_pdf → classify_pages or handle_error
    builder.set_entry_point("burst_pdf")
    builder.add_conditional_edges(
        "burst_pdf",
        _route_after_burst,
        {"classify_pages": "classify_pages", "handle_error": "handle_error"},
    )
    builder.add_edge("handle_error", END)
    builder.add_edge("classify_pages", "extract_parallel")
    builder.add_edge("extract_parallel", "merge_extractions")
    builder.add_edge("merge_extractions", "normalize")
    builder.add_edge("normalize", "fetch_api")
    builder.add_edge("fetch_api", "verify")

    # Conditional: verify → route_hitl → persist or human_review
    builder.add_conditional_edges(
        "verify",
        _route_hitl,
        {
            "persist": "persist",
            "human_review": "human_review",
        },
    )
    builder.add_edge("human_review", "persist")
    builder.add_edge("persist", END)

    # Compile with PostgresSaver when available (Task 3.2)
    checkpointer = get_checkpointer()
    graph = builder.compile(checkpointer=checkpointer)
    return graph


# Singleton compiled graph
_avae_graph = None


def get_avae_graph():
    """Get or create the compiled AVAE graph."""
    global _avae_graph
    if _avae_graph is None:
        _avae_graph = build_avae_graph()
    return _avae_graph
