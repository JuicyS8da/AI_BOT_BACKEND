from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.common.db import get_async_session
from app.common.common import CurrentUser
from app.users.models import User
from app.quiz import crud, schemas
from app.quiz.models import Quiz, QuizQuestion, UserAnswer
from app.events.models import Event
from datetime import datetime, timezone


class QuizService:
    def __init__(self, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(CurrentUser())):
        self.session = session
        self.current_user = current_user

    # ---- Quiz ----
    async def get_quiz(self, quiz_id: int) -> Quiz:
        result = await self.session.execute(select(Quiz).where(Quiz.id == quiz_id))
        quiz = result.scalar_one_or_none()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return quiz

    async def create_quiz(self, data: schemas.QuizCreate) -> Quiz:
        if not self.current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")
        return await crud.create_quiz(self.session, data)

    async def list_quizzes(self) -> list[Quiz]:
        return await crud.list_quizzes(self.session)

    async def update_quiz(self, quiz_id: int, data: schemas.QuizUpdate) -> Quiz:
        if not self.current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")
        return await crud.update_quiz(self.session, quiz_id, data)

    async def delete_quiz(self, quiz_id: int) -> None:
        await crud.delete_quiz(self.session, quiz_id)

    # ---- QuizQuestion ----
    async def list_questions(self, quiz_id: int) -> list[QuizQuestion]:
        return await crud.list_questions(self.session, quiz_id)

    async def create_question(self, data: schemas.QuizQuestionCreate) -> QuizQuestion:
        if not self.current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")
        return await crud.create_question(self.session, data)

    async def get_question(self, question_id: int) -> QuizQuestion:
        return await crud.get_question(self.session, question_id)

    async def update_question(self, question_id: int, data: schemas.QuizQuestionUpdate) -> QuizQuestion:
        if not self.current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")
        return await crud.update_question(self.session, question_id, data)

    async def delete_question(self, question_id: int) -> None:
        if not self.current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin rights required")
        await crud.delete_question(self.session, question_id)

    # ---- UserAnswer ----
    async def create_user_answer(self, data: schemas.UserAnswerCreate) -> UserAnswer:
        return await crud.create_user_answer(self.session, data)

    async def list_user_answers(self, question_id: int) -> list[UserAnswer]:
        return await crud.list_user_answers(self.session, question_id)

    async def get_user_answer(self, answer_id: int) -> UserAnswer:
        return await crud.get_user_answer(self.session, answer_id)

    # ---- Current Question Logic ----
    async def get_current_question(self, event_id: int):
        result = await self.session.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        result = await self.session.execute(
            select(QuizQuestion).where(QuizQuestion.event_id == event_id).order_by(QuizQuestion.id)
        )
        questions = result.scalars().all()
        if not questions:
            raise HTTPException(status_code=404, detail="No questions")

        if event.current_question_index >= len(questions):
            raise HTTPException(status_code=400, detail="Event finished")

        current_question = questions[event.current_question_index]

        now = datetime.now(timezone.utc)
        elapsed = (now - current_question.start_time).total_seconds()
        time_left = current_question.duration_seconds - int(elapsed)
        if time_left < 0:
            time_left = 0

        return {
            "question_index": event.current_question_index,
            "question_text": current_question.text,
            "total_questions": len(questions),
            "time_left_seconds": time_left,
        }
