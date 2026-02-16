"""Team invite API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter()


class InviteRequest(BaseModel):
    project_id: str
    email: EmailStr


class InviteResponse(BaseModel):
    id: str
    email: str
    status: str
    project_id: str


@router.post("/api/invites", response_model=InviteResponse)
async def send_invite(request: InviteRequest):
    """Send a team invite email and track it."""
    import uuid

    invite_id = str(uuid.uuid4())

    # TODO: Send actual email via SendGrid/Resend
    # TODO: Store in database

    return InviteResponse(
        id=invite_id,
        email=request.email,
        status="pending",
        project_id=request.project_id,
    )


@router.get("/api/invites")
async def list_invites(project_id: str):
    """List all invites for a project."""
    # TODO: Fetch from database
    return {"invites": [], "project_id": project_id}
