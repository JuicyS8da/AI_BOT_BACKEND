from fastapi import APIRouter, Depends

from app.events.services import EventService
from app.common.common import CurrentUser
from app.users.models import User

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/create")
async def create_event(
    name: str,
    service: EventService = Depends(),
    user: User = Depends(CurrentUser()),
):
    return await service.create_event(name=name)


@router.get("/{event_id}/next_phase")
async def next_event_phase(
    event_id: int,
    service: EventService = Depends(),
    user: User = Depends(CurrentUser(require_admin=True)),
):
    event = await service.next_phase(event_id)
    return {
        "game_status": event.status,
        "current_question_index": event.current_question_index,
    }


@router.get("/{event_id}")
async def get_event_status(event_id: int, service: EventService = Depends()):
    event = await service.get_event_status(event_id)
    return {
        "game_status": event.status,
        "current_question_index": event.current_question_index,
    }

@router.get("/")
async def list_events(service: EventService = Depends()):
    return await service.list_events()