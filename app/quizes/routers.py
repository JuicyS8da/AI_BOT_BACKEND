from datetime import datetime, timezone
from sqlalchemy import select

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.db import get_async_session
from app.common.common import CurrentUser
from app.users.models import User
from app.quizes import schemas
from app.quizes.models import Quiz, QuizQuestion
from app.quizes.services import QuizService


router = APIRouter(prefix="/quizes", tags=["quizes"])

@router.post("/create", response_model=schemas.QuizOut)
async def create_quiz(data: schemas.QuizCreate, session: AsyncSession = Depends(get_async_session)):
    quiz = Quiz(
        name=data.name,
        description=data.description,
    )
    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)
    return quiz


@router.get("/list", response_model=list[schemas.QuizOut])
async def list_quizes(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Quiz))
    return result.scalars().all()

@router.post("/add", response_model=schemas.QuizQuestionOut)
async def add_question(data: schemas.QuizQuestionCreate, session: AsyncSession = Depends(get_async_session)):
    service = QuizService(session)
    return await service.add_question(data)

@router.get("/{question_id}", response_model=schemas.QuizQuestionOut)
async def get_question(question_id: int, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(QuizQuestion).where(QuizQuestion.id == question_id))
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
        "quiz_id": question.quiz_id,
    }

@router.get("/list")
async def list_questions(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(QuizQuestion))
    return result.scalars().all()

@router.post("/answer")
async def submit_answer(data: schemas.UserAnswerCreate, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(CurrentUser())):
    service = QuizService(session, current_user)
    return await service.submit_answer(data)

@router.get("/{quiz_id}")
async def get_quiz_questions_list(quiz_id: int, session: AsyncSession = Depends(get_async_session)):
    service = QuizService(session)
    return await service.get_quiz_questions_list(quiz_id=quiz_id)
