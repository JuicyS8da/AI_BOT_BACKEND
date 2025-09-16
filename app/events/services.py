from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.common.db import get_async_session
from app.common.common import CurrentUser
from app.users.models import User
from app.events.models import Event, EventStatus


class EventService:
    def __init__(self, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(CurrentUser())):
        self.session = session
        self.current_user = current_user

    async def list_events(self) -> list[Event]:
        result = await self.session.execute(select(Event))
        return result.scalars().all()

    async def create_event(self, name: str, creator_id: int) -> Event:
        if not self.current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")

        result = await self.session.execute(
            select(Event).where(Event.status == EventStatus.STARTED)
        )
        active_event = result.scalar_one_or_none()
        if active_event:
            raise HTTPException(status_code=400, detail="Another event is already active")

        new_event = Event(
            name=name,
            creator_id=creator_id,
            status=EventStatus.NOT_STARTED,
        )

        self.session.add(new_event)
        await self.session.commit()
        await self.session.refresh(new_event)

        return new_event

    async def next_phase(self, event_id: int) -> Event:
        if not self.current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")
        result = await self.session.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        if event.status == EventStatus.NOT_STARTED:
            event.status = EventStatus.REGISTRATION
        elif event.status == EventStatus.REGISTRATION:
            event.status = EventStatus.STARTED
        elif event.status == EventStatus.STARTED:
            event.status = EventStatus.FINISHED
        else:
            raise HTTPException(status_code=400, detail="Event already finished")

        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def get_event_status(self, event_id: int) -> Event:
        result = await self.session.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event
