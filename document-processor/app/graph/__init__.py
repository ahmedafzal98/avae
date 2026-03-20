"""
AVAE LangGraph orchestration (Phase 3, Task 3.1).

Pipeline: burst_pdf → classify_pages → extract_parallel → normalize
          → fetch_api → verify → route_hitl → [persist | human_review → persist]
"""
from app.graph.graph import get_avae_graph, build_avae_graph
from app.graph.state import AVAEState


def run_avae_graph(
    task_id: str,
    s3_bucket: str,
    s3_key: str,
    filename: str,
    audit_target: str = "epc",
    prompt: str = "",
) -> dict:
    """
    Run the AVAE verification graph.

    Args:
        task_id: Document ID
        s3_bucket: S3 bucket name
        s3_key: S3 object key
        filename: Original filename
        audit_target: epc, companies_house, hm_land_registry
        prompt: Optional summary prompt (not used in graph yet)

    Returns:
        Final state dict after graph execution
    """
    graph = get_avae_graph()
    initial_state: AVAEState = {
        "task_id": task_id,
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
        "filename": filename,
        "audit_target": audit_target,
        "prompt": prompt,
    }
    config = {"configurable": {"thread_id": task_id}}
    final_state = graph.invoke(initial_state, config)
    return final_state


__all__ = ["run_avae_graph", "get_avae_graph", "build_avae_graph", "AVAEState"]
