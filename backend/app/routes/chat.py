"""Chat endpoint — POST /api/chat → SSE stream."""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.agent import generate_response
from app.models import ChatRequest
from app.sse_bridge import stream_sse_events

router = APIRouter()


@router.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    """Send a message, receive streaming SSE response.

    Events emitted: text, error, done.
    """
    event_source = generate_response(
        message=request.message,
        session_id=request.session_id,
        context=request.context,
    )
    return EventSourceResponse(
        stream_sse_events(event_source),
        media_type="text/event-stream",
    )
