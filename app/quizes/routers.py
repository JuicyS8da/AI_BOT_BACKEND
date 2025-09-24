import json

from datetime import datetime, timezone
from sqlalchemy import select

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.db import get_async_session
from app.common.common import CurrentUser
from app.users.models import User
from app.events.models import Event
from app.quizes import schemas
from app.quizes.models import Quiz, QuizQuestion
from app.quizes.services import QuizService


router = APIRouter(prefix="/quizes", tags=["quizes"])

@router.post("/create", response_model=schemas.QuizOut)
async def create_quiz(data: schemas.QuizCreate, session: AsyncSession = Depends(get_async_session)):
    # убедимся, что событие есть
    if not (await session.scalar(select(Event.id).where(Event.id == data.event_id))):
        raise HTTPException(404, "Event not found")

    q = Quiz(
        name=data.name,
        description=data.description,
        is_active=data.is_active,
        event_id=data.event_id,
    )
    session.add(q)
    await session.commit()
    await session.refresh(q)
    return q

@router.get("/quizes/by-event/{event_id}", response_model=list[schemas.QuizOut])
async def list_quizes_by_event(event_id: int, session: AsyncSession = Depends(get_async_session)):
    res = await session.execute(select(Quiz).where(Quiz.event_id == event_id).order_by(Quiz.id))
    return [schemas.QuizOut.model_validate(x) for x in res.scalars().all()]



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


@router.get("/questions/list", response_model=list[schemas.QuizQuestionOut], summary="Question list by quiz_id")
async def list_questions(session: AsyncSession = Depends(get_async_session), current_user: User = Depends(CurrentUser()), quiz_id: int = Query(..., description="ID квиза")):
    service = QuizService(session, current_user)
    return await service.list_questions_by_quiz(quiz_id)

@router.post("/answer")
async def submit_answer(data: schemas.UserAnswerCreate, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(CurrentUser())):
    service = QuizService(session, current_user)
    return await service.submit_answer(data)

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

@router.get("/{quiz_id}/questions", response_model=list[schemas.QuizQuestionLocalizedOut], summary="Список вопросов квиза, локализованный",)
async def list_questions_localized(
    quiz_id: int,
    locale: str = Query("ru", description="Код языка, например: ru, kk, en"),
    include_correct: bool = Query(False, description="Включать ли правильные ответы (для админки)"),
    svc: QuizService = Depends(),
):
    return await svc.list_questions_by_quiz_locale(
        quiz_id=quiz_id,
        locale=locale,
        include_correct=include_correct,
    )