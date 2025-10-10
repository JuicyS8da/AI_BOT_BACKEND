import json

from sqlalchemy import select

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form, Request, Body
from typing import List, Optional
from starlette import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.db import get_async_session
from app.common.common import CurrentUser
from app.common.files import save_file_for_quiz
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


@router.post(
    "/{quiz_id}/questions:add_json",
    response_model=schemas.QuizQuestionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить вопрос (application/json)",
)
async def add_quiz_question_json(
    request: Request,
    quiz_id: int,
    session: AsyncSession = Depends(get_async_session),
    body: schemas.QuizQuestionCreate = Body(
        ...,
        example={
            "type": "single",
            "text_i18n": {"ru": "Что изображено на картинке?"},
            "options_i18n": {"ru": ["Кот", "Собака", "Лошадь"]},
            "correct_answers_i18n": {"ru": ["Кот"]},
            "duration_seconds": 30,
            "points": 3
        },
    ),
):
    svc = QuizService(session)
    body.quiz_id = quiz_id
    return await svc.create_quiz_question(body)

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

@router.post(
    "/{quiz_id}/questions:bulk_import_with_images_file",
    response_model=schemas.QuizQuestionsBulkOut,
    summary="Bulk import questions (JSON file) + images (multipart/form-data)"
)
async def bulk_import_with_images_file(
    quiz_id: int,
    payload_file: UploadFile = File(..., description="JSON-файл с вопросами (формат как в bulk_import_questions_file)"),
    images: list[UploadFile] = File(default=[], description="Набор изображений; сопоставляются по индексу с вопросами"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Пример `multipart/form-data`:
    - payload_file: questions.json (содержит { "items": [ ... ] })
    - images: file1.png
    - images: file2.jpg
    ...

    Маппинг: images[i] -> items[i].image_url
    """
    # 1) читаем и разбираем JSON
    try:
        raw = await payload_file.read()
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}")

    try:
        bulk_in = schemas.QuizQuestionsBulkIn.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid payload schema: {e}")

    # 2) сохраняем картинки и собираем URL-ы
    image_urls: list[str] = []
    for f in images:
        url = await save_file_for_quiz(quiz_id, f)  # вернёт вида /media/quizes/<quiz_id>/<uuid>.ext
        image_urls.append(url)

    # 3) поиндексно дописываем image_url в элементы
    for i, item in enumerate(bulk_in.items):
        if i < len(image_urls):
            item.image_url = image_urls[i]

    # 4) пишем в БД
    svc = QuizService(session)
    return await svc.bulk_add_questions_simple(quiz_id, bulk_in)

@router.post(
    "/questions/{question_id}/images:attach",
    response_model=schemas.QuizQuestionOut,
    summary="Прикрепить картинки к существующему вопросу",
)
async def attach_images(
    request: Request,
    question_id: int,
    session: AsyncSession = Depends(get_async_session),
    images: List[UploadFile] = File(..., description="Файлы изображений"),
):
    svc = QuizService(session)
    q = await svc.attach_images_to_question(question_id=question_id, request=request, images=images)
    return schemas.QuizQuestionOut.model_validate(q)


@router.post(
    "/{quiz_id}/questions:bulk_import_with_images",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk: JSON-манифест + файлы",
)
async def bulk_import_with_images(
    quiz_id: int,
    request: Request,
    manifest: str = Form(..., description="JSON-манифест (см. пример)"),
    files: List[UploadFile] = File(default=[]),
    svc: QuizService = Depends(),
):
    """
    Пример manifest:
    {
      "defaults": {"duration_seconds": 30, "points": 3},
      "items": [
        {
          "type": "multiple",
          "text_i18n": {"ru": "Оптика изучает что?"},
          "options_i18n": {"ru": ["Звук","Тепло","Свет","Электричество"]},
          "correct_answers_i18n": {"ru": ["Свет"]},
          "images": ["optics1.jpg","optics2.png"]
        }
      ]
    }
    """
    return await svc.bulk_add_questions_with_files(quiz_id, request, manifest, files)