# ex3_extraction/batch.py
"""
Message Batches API for latency-tolerant document extraction.

Key rules from the exam guide:
  - 50% cost savings vs synchronous API
  - Up to 24-hour processing window (no guaranteed latency SLA)
  - NOT suitable for blocking workflows (pre-merge checks)
  - Use custom_id to correlate requests/responses
  - On failure: resubmit only failed documents (by custom_id)
"""
import time
from shared.client import get_client, MODEL
from ex3_extraction.schema import get_extraction_tool


def build_batch_request(custom_id: str, document_text: str) -> dict:
    """Build a single batch request item."""
    return {
        "custom_id": custom_id,
        "params": {
            "model": MODEL,
            "max_tokens": 2048,
            "tools": [get_extraction_tool()],
            "tool_choice": {"type": "tool", "name": "extract_document"},
            "messages": [{"role": "user", "content": f"Extract data:\n\n{document_text}"}],
        },
    }


def submit_batch(documents: dict[str, str]) -> str:
    """
    Submit a batch of documents. Returns batch_id.
    documents: {custom_id: document_text}
    """
    client = get_client()
    requests = [build_batch_request(cid, text) for cid, text in documents.items()]
    batch = client.messages.batches.create(requests=requests)
    return batch.id


def poll_batch(batch_id: str, poll_interval: int = 60) -> dict:
    """
    Poll until batch completes. Returns {custom_id: result_dict}.
    poll_interval: seconds between polls (default 60s for production; use 5s for testing)
    """
    client = get_client()
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            break
        time.sleep(poll_interval)

    results = {}
    for result in client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            for block in result.result.message.content:
                if block.type == "tool_use":
                    results[result.custom_id] = {"status": "success", "data": block.input}
        else:
            results[result.custom_id] = {
                "status": "failed",
                "error": str(result.result),
            }
    return results


def handle_failures(batch_results: dict, original_docs: dict[str, str]) -> dict:
    """
    Identify failed extractions and prepare resubmission dict.
    Returns {custom_id: document_text} for failed documents.
    """
    return {
        custom_id: original_docs[custom_id]
        for custom_id, result in batch_results.items()
        if result["status"] == "failed" and custom_id in original_docs
    }
