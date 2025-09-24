import json

from datetime import datetime, timezone
from sqlalchemy import select

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
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


@router.get("quizes/list", response_model=list[schemas.QuizOut])
async def list_quizes(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Quiz))
    return result.scalars().all()

@router.post("/add", response_model=schemas.QuizQuestionOut)
async def add_question(data: schemas.QuizQuestionCreate, session: AsyncSession = Depends(get_async_session)):
    service = QuizService(session)
    return await service.add_question(data)

def _to_out(q: QuizQuestion) -> dict:
    """Преобразование ORM → dict для ответа (если не используете Pydantic.from_attributes)."""
    return {
        "id": q.id,
        "quiz_id": q.quiz_id,
        "type": q.type.value if q.type else None,
        "text": q.text_i18n,
        "options": q.options_i18n,
        "correct_answers": q.correct_answers_i18n,
        "duration_seconds": q.duration_seconds,
        "points": q.points,
    }


@router.get("/{question_id}", response_model=schemas.QuizQuestionOut)
async def get_question(
    question_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    res = await session.execute(
        select(QuizQuestion).where(QuizQuestion.id == question_id)
    )
    question = res.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # если схемы настроены на from_attributes=True — вернём напрямую
    return schemas.QuizQuestionOut.model_validate(question)
    # если не используете Pydantic.from_attributes, верните:
    # return _to_out(question)


@router.get("/list", response_model=list[schemas.QuizQuestionOut])
async def list_questions(
    session: AsyncSession = Depends(get_async_session),
    quiz_id: int | None = Query(default=None, description="Фильтр по квизу"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    stmt = select(QuizQuestion).order_by(QuizQuestion.id).limit(limit).offset(offset)
    if quiz_id is not None:
        stmt = stmt.where(QuizQuestion.quiz_id == quiz_id)

    res = await session.execute(stmt)
    items = res.scalars().all()

    # Pydantic v2: from_attributes
    return [schemas.QuizQuestionOut.model_validate(q) for q in items]
    # либо без схем — так:
    # return [_to_out(q) for q in items]

@router.post("/answer")
async def submit_answer(data: schemas.UserAnswerCreate, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(CurrentUser())):
    service = QuizService(session, current_user)
    return await service.submit_answer(data)

@router.get("/{quiz_id}")
async def get_quiz_questions_list(quiz_id: int, session: AsyncSession = Depends(get_async_session)):
    service = QuizService(session)
    return await service.get_quiz_questions_list(quiz_id=quiz_id)

@router.get("/{quiz_id}/start")
async def start_quiz(quiz_id: int, session: AsyncSession = Depends(get_async_session)):
    service = QuizService(session)
    await service.toggle_quiz_active(quiz_id=quiz_id, is_active=True)
    return {"message": "Quiz has been activated"}

@router.get("/{quiz_id}/stop")
async def stop_quiz(quiz_id: int, session: AsyncSession = Depends(get_async_session)):
    service = QuizService(session)
    await service.toggle_quiz_active(quiz_id=quiz_id, is_active=False)
    return {"message": "Quiz has been deactivated"}

@router.post("/{quiz_id}/questions:bulk_import", response_model=schemas.QuizQuestionsBulkOut, summary="Bulk import questions (JSON body)")
async def bulk_import_questions(
    quiz_id: int,
    payload: schemas.QuizQuestionsBulkIn,
    svc: QuizService = Depends(),
):
    """
    Пример тела:
    {
      "items": [
        {
          "type": "multiple",
          "text_i18n": {"ru": "Выберите гласные"},
          "options_i18n": {"ru": ["А", "Б", "Е", "Ж"]},
          "correct_answers_i18n": {"ru": ["А", "Е"]},
          "duration_seconds": 45,
          "points": 2
        },
        {
          "type": "open",
          "text_i18n": {"ru": "Столица Казахстана?"},
          "correct_answers_i18n": {"ru": ["Астана", "Нур-Султан"]},
          "duration_seconds": 60,
          "points": 1
        }
      ]
    }
    """
    return await svc.bulk_add_questions(quiz_id, payload)

@router.post("/{quiz_id}/questions:bulk_import_file", response_model=schemas.QuizQuestionsBulkOut, summary="Bulk import questions (upload JSON file)")
async def bulk_import_questions_file(
    quiz_id: int,
    file: UploadFile = File(..., description="JSON файл: либо массив объектов, либо {\"items\": [...]}"),
    svc: QuizService = Depends(),
):
    raw = await file.read()
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # принимаем и массив, и {"items": [...]}
    items = data.get("items", data)
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="Expected a list of items or {\"items\": [...]}")

    payload = schemas.QuizQuestionsBulkIn(items=items)  # Pydantic сам валидирует по QuizQuestionUpsert
    return await svc.bulk_add_questions(quiz_id, payload)