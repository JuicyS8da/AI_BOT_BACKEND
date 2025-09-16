from datetime import datetime, timezone
from sqlalchemy import select

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.db import get_async_session
from app.common.common import CurrentUser
from app.users.models import User
from app.minigames import schemas
from app.minigames.models import Minigame, MinigameQuestion
from app.minigames.services import MinigameService


router = APIRouter(prefix="/minigames", tags=["minigames"])

@router.post("/create", response_model=schemas.MinigameOut)
async def create_minigame(data: schemas.MinigameCreate, session: AsyncSession = Depends(get_async_session)):
    minigame = Minigame(
        name=data.name,
        description=data.description,
        duration_seconds=data.duration_seconds,
        start_time=data.start_time,   # используем поле из схемы
    )
    session.add(minigame)
    await session.commit()
    await session.refresh(minigame)
    return minigame


@router.get("/list", response_model=list[schemas.MinigameOut])
async def list_minigames(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Minigame))
    return result.scalars().all()

@router.post("/add", response_model=schemas.MinigameQuestionOut)
async def add_question(data: schemas.MinigameQuestionCreate, session: AsyncSession = Depends(get_async_session)):
    service = MinigameService(session)
    return await service.add_question(data)

@router.get("/{question_id}", response_model=schemas.MinigameQuestionOut)
async def get_question(question_id: int, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(MinigameQuestion).where(MinigameQuestion.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    q_type = "open" if not question.correct_answers else "single" if len(question.correct_answers) == 1 else "multiple"
    return {
        "id": question.id,
        "text": question.text,
        "correct_answers": question.correct_answers,
        "points": question.points,
        "type": q_type,
        "minigame_id": question.minigame_id,
    }

@router.get("/list")
async def list_questions(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(MinigameQuestion))
    return result.scalars().all()

@router.post("/answer", response_model=schemas.UserAnswerResponse)
async def submit_answer(data: schemas.UserAnswerCreate, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(CurrentUser())):
    service = MinigameService(session, current_user)
    return await service.submit_answer(data)