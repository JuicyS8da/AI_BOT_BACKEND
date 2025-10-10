from typing import List, Optional, Annotated
from fastapi import UploadFile, Request

import unicodedata, json

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.common.db import get_async_session
from app.common.common import CurrentUser
from app.users.models import User
from app.quizes import schemas
from app.quizes.models import Quiz, QuizQuestion, QuizUserAnswer, QuestionType
from app.common.files import _save_uploads, save_upload




def _normalize(s: str) -> str:
    # мягкая нормализация для open-ended
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s).casefold().strip()
    # при желании — удаление диакритики:
    s = "".join(ch for ch in unicodedata.normalize("NFD", s) if not unicodedata.combining(ch))
    return s

class QuizService:
    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(CurrentUser()),
    ):
        self.session = session
        self.current_user = current_user

    async def _get_question(self, question_id: int) -> QuizQuestion:
        res = await self.session.execute(select(QuizQuestion).where(QuizQuestion.id == question_id))
        q = res.scalar_one_or_none()
        if not q:
            raise HTTPException(status_code=404, detail="Question not found")
        return q

    def _get_locale_correct(self, question: QuizQuestion, locale: str, fallback: str = "ru") -> List[str]:
        if not locale:
            locale = fallback
        return question.correct_answers_i18n.get(locale) or question.correct_answers_i18n.get(fallback) or []

    def _get_locale_options(self, question: QuizQuestion, locale: str, fallback: str = "ru") -> List[str]:
        if not locale:
            locale = fallback
        return question.options_i18n.get(locale) or question.options_i18n.get(fallback) or []

    async def calculate_points(self, question: QuizQuestion, user_answer: str | List[str], locale: str) -> int:
        qtype = question.type  # явный enum
        correct = self._get_locale_correct(question, locale)

        # приводим пользовательский ответ к списку строк
        if isinstance(user_answer, list):
            user_list = [str(x) for x in user_answer]
        else:
            user_list = [str(user_answer)]

        if qtype == QuestionType.OPEN:
            # зачёт, если хоть один из вариантов совпал после нормализации
            u = _normalize(user_list[0]) if user_list else ""
            return int(any(u == _normalize(ans) for ans in correct))

        if qtype == QuestionType.SINGLE:
            # ожидаем ровно 1 ответ
            if len(user_list) != 1 or not correct:
                return 0
            return question.points if user_list[0] == correct[0] else 0

        if qtype == QuestionType.MULTIPLE:
            # сравниваем как множества; частичный зачёт — пропорцией
            correct_set = set(correct)
            user_set = set(user_list)
            if not correct_set:
                return 0
            if user_set == correct_set:
                return question.points
            # частичный зачёт (можно отключить, если не надо)
            overlap = len(user_set & correct_set)
            return int(question.points * overlap / len(correct_set))

        return 0  # на всякий случай

    async def submit_answer(self, data: schemas.UserAnswerCreate) -> dict:
        """
        Возвращает:
        {
            "answer_id": int,
            "awarded_points": int,
            "user_points_total": int
        }
        """
        question = await self._get_question(data.question_id)

        # Сохраняем ответ пользователя
        answers_list = data.answers if isinstance(data.answers, list) else [str(data.answers)]
        user_answer = QuizUserAnswer(
            user_id=self.current_user.id,
            question_id=question.id,
            quiz_id=question.quiz_id,
            answers=answers_list,
            locale=getattr(data, "locale", "ru"),
        )
        self.session.add(user_answer)
        await self.session.flush()  # получим id без коммита

        # Считаем очки
        locale = getattr(data, "locale", "ru")
        points = await self.calculate_points(question, data.answers, locale)

        # Обновляем пользователя
        self.current_user.points = (self.current_user.points or 0) + points
        self.session.add(self.current_user)

        await self.session.commit()
        await self.session.refresh(user_answer)
        await self.session.refresh(self.current_user)

        # Возвращаем JSON с очками
        return {
            "answer_id": user_answer.id,
            "awarded_points": points,
            "user_points_total": self.current_user.points,
        }


    async def _get_question(self, question_id: int) -> QuizQuestion:
        res = await self.session.execute(select(QuizQuestion).where(QuizQuestion.id == question_id))
        q = res.scalar_one_or_none()
        if not q:
            raise HTTPException(status_code=404, detail="Question not found")
        return q

    async def create_quiz_question(
        self,
        data: schemas.QuizQuestionCreate,
        request: Optional[Request] = None,
        images: Optional[List[UploadFile]] = None,
    ) -> QuizQuestion:

        images_urls: List[str] = []
        # 1) если прислали готовые ссылки в JSON
        if data.images_urls:
            images_urls.extend([str(u) for u in data.images_urls])

        # 2) если прислали файлы — сохраняем
        if images:
            if request is None:
                raise HTTPException(500, detail="Request is required when uploading files")
            saved = await _save_uploads(request, images, subdir="questions")
            images_urls.extend(saved)

        q = QuizQuestion(
            type=QuestionType(data.type) if isinstance(data.type, str) else data.type,
            text_i18n=data.text_i18n or {},
            options_i18n=data.options_i18n or {},
            correct_answers_i18n=data.correct_answers_i18n or {},
            duration_seconds=data.duration_seconds,
            points=data.points,
            quiz_id=data.quiz_id,
            images_urls=images_urls,
        )
        self.session.add(q)
        await self.session.commit()
        await self.session.refresh(q)
        return q

    async def get_quiz_questions_list(self, quiz_id: int, locale: str = "ru"):
        res = await self.session.execute(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id))
        items = res.scalars().all()
        # отдадим уже «под конкретную локаль»
        out = []
        for q in items:
            out.append({
                "id": q.id,
                "type": q.type.value,
                "text": q.text_i18n.get(locale) or next(iter(q.text_i18n.values()), ""),
                "options": self._get_locale_options(q, locale),
                "duration_seconds": q.duration_seconds,
                "points": q.points,
            })
        return out

    async def list_questions_by_quiz(self, quiz_id: int) -> list[schemas.QuizQuestionOut]:
        stmt = (
            select(QuizQuestion)
            .where(QuizQuestion.quiz_id == quiz_id)
            .order_by(QuizQuestion.id)
        )
        res = await self.session.execute(stmt)
        items = res.scalars().all()

        # Pydantic v2: from_attributes=True, чтобы читать из ORM-объектов
        return [schemas.QuizQuestionOut.model_validate(q, from_attributes=True) for q in items]

    async def toggle_quiz_active(self, quiz_id: int, is_active: bool):
        # фикс: в модели у Quiz поле id, а не quiz_id
        res = await self.session.execute(select(Quiz).where(Quiz.id == quiz_id))
        quiz = res.scalar_one_or_none()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        quiz.is_active = is_active
        self.session.add(quiz)
        await self.session.commit()
        await self.session.refresh(quiz)
        return {"id": quiz.id, "is_active": quiz.is_active}
    
    async def bulk_add_questions(self, quiz_id: int, payload: schemas.QuizQuestionsBulkIn) -> dict:
        # 1) проверим, что квиз существует
        res = await self.session.execute(select(Quiz).where(Quiz.id == quiz_id))
        quiz = res.scalar_one_or_none()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        created_ids: list[int] = []
        try:
            for item in payload.items:
                data = item.model_dump()
                qtype = data["type"]
                if isinstance(qtype, str):
                    qtype = QuestionType(qtype)
                question = QuizQuestion(
                    type=qtype,
                    text_i18n=data["text_i18n"],
                    options_i18n=data.get("options_i18n", {}),
                    correct_answers_i18n=data.get("correct_answers_i18n", {}),
                    duration_seconds=data.get("duration_seconds"),
                    points=data.get("points", 1),
                    quiz_id=quiz_id,
                )
                self.session.add(question)
                await self.session.flush()  # получить id без коммита
                created_ids.append(question.id)

            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return {"created": len(created_ids), "ids": created_ids}
    
    async def list_questions_by_quiz_locale(self, quiz_id: int, locale: str = "ru", include_correct: bool = False) -> list[schemas.QuizQuestionLocalizedOut]:
        stmt = (
            select(QuizQuestion)
            .where(QuizQuestion.quiz_id == quiz_id)
            .order_by(QuizQuestion.id)
        )
        res = await self.session.execute(stmt)
        items = res.scalars().all()

        out: list[schemas.QuizQuestionLocalizedOut] = []
        for q in items:
            # текст с фолбэком на первую доступную локаль
            text = q.text_i18n.get(locale) or next(iter(q.text_i18n.values()), "")

            # варианты под локаль (для OPEN будет пусто, и это ок)
            options = self._get_locale_options(q, locale)

            payload = {
                "id": q.id,
                "type": q.type,  # Enum -> сериализуется как "single"/...
                "text": text,
                "options": options,
                "duration_seconds": q.duration_seconds,
                "points": q.points,
                "images_urls": q.images_urls or [],
            }

            # если надо получить и правильные ответы (например, для админки):
            if include_correct:
                correct = self._get_locale_correct(q, locale)
                payload["correct_answers"] = correct  # добавь поле в схему, если нужно

            out.append(schemas.QuizQuestionLocalizedOut(**payload))

        return out
    
    async def attach_images_to_question(
        self,
        question_id: int,
        request: Request,
        images: List[UploadFile],
    ) -> QuizQuestion:
        q = await self._get_question(question_id)
        saved = await _save_uploads(request, images, subdir=f"questions/{question_id}")
        q.images_urls = (q.images_urls or []) + saved
        self.session.add(q)
        await self.session.commit()
        await self.session.refresh(q)
        return q
    
    async def bulk_add_questions_with_files(self, quiz_id: int, request, manifest_str: str, files: List):
        # 1) валидация квиза
        res = await self.session.execute(select(Quiz).where(Quiz.id == quiz_id))
        quiz = res.scalar_one_or_none()
        if not quiz:
            raise HTTPException(404, "Quiz not found")

        # 2) парсим JSON
        try:
            manifest = json.loads(manifest_str)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid manifest JSON")

        defaults = manifest.get("defaults", {})
        items = manifest.get("items", [])
        if not isinstance(items, list) or not items:
            raise HTTPException(400, "Empty items")

        # 3) сопоставление имени файла -> UploadFile
        file_map = {f.filename: f for f in (files or []) if f and f.filename}

        created_ids = []
        try:
            for item in items:
                data = {
                    "type": item["type"],
                    "text_i18n": item.get("text_i18n", {}),
                    "options_i18n": item.get("options_i18n", {}),
                    "correct_answers_i18n": item.get("correct_answers_i18n", {}),
                    "duration_seconds": item.get("duration_seconds", defaults.get("duration_seconds")),
                    "points": item.get("points", defaults.get("points", 1)),
                    "quiz_id": quiz_id,
                }
                q = QuizQuestion(
                    type=QuestionType(data["type"]) if isinstance(data["type"], str) else data["type"],
                    text_i18n=data["text_i18n"],
                    options_i18n=data["options_i18n"],
                    correct_answers_i18n=data["correct_answers_i18n"],
                    duration_seconds=data["duration_seconds"],
                    points=data["points"],
                    quiz_id=data["quiz_id"],
                )
                self.session.add(q)
                await self.session.flush()   # получить q.id

                # 4) сохраняем все прикреплённые картинки
                image_names = item.get("images", []) or []
                saved_urls = []
                for name in image_names:
                    uf = file_map.get(name)
                    if not uf:
                        continue  # можно ругаться, можно пропускать
                    url = await save_upload(request, uf, subdir=f"questions/{q.id}")
                    # если у тебя images хранятся JSON-списком URL — добавь поле images_json у модели
                    saved_urls.append(url)

                # если модель хранит одно поле image_url — сохрани первую
                if saved_urls:
                    q.image_url = saved_urls[0]

                await self.session.flush()
                created_ids.append(q.id)

            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return {"created": len(created_ids), "ids": created_ids}
    
    async def get_leaderboard(self, limit: int = 10):
        stmt = (
            select(User)
            .where(User.is_active == True)
            .order_by(desc(User.points))
            .limit(limit)   
        )
        res = await self.session.execute(stmt)
        users = res.scalars().all()

        return [
            schemas.UserLeaderboardOut(
                telegram_id=u.telegram_id,
                nickname=u.nickname,
                first_name=u.first_name,
                last_name=u.last_name,
                points=u.points or 0
            )
            for u in users
        ]