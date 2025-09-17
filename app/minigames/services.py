from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.common.db import AsyncSession, get_async_session
from app.common.common import CurrentUser
from app.users.models import User
from app.minigames import schemas
from app.minigames.models import Minigame, MinigameQuestion, MinigameUserAnswer
from app.minigames.schemas import MinigameQuestionCreate



class MinigameService:
    def __init__(self, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(CurrentUser())):
        self.session = session
        self.current_user = current_user

    def get_question_type(self, question: MinigameQuestion) -> str:
        if not question.correct_answers:
            return "open"
        elif len(question.correct_answers) == 1:
            return "single"
        else:
            return "multiple"

    async def calculate_points(self, question: MinigameQuestion, user_answer: str | list[str]) -> int:
        q_type = self.get_question_type(question)

        # open-ended — пока всегда 0
        if q_type == "open-ended":
            return 0

        # single answer
        if q_type == "single":
            return question.points if user_answer == question.correct_answers[0] else 0

        # multiple answers
        if q_type == "multiple":
            if not isinstance(user_answer, list):
                return 0
            correct = set(question.correct_answers)
            user_ans = set(user_answer)
            if user_ans == correct:
                return question.points
            # частичное совпадение
            return int(question.points * len(user_ans & correct) / len(correct))

        return 0

    async def submit_answer(self, data: schemas.UserAnswerCreate) -> MinigameUserAnswer:
        # находим вопрос
        result = await self.session.execute(
            select(MinigameQuestion).where(MinigameQuestion.id == data.question_id)
        )
        question = result.scalar_one_or_none()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # создаём ответ
        user_answer = MinigameUserAnswer(
            user_id=self.current_user.id,
            question_id=question.id,
            minigame_id=question.minigame_id,
            answer=data.answer
        )
        self.session.add(user_answer)
        await self.session.flush()  # чтобы был id, но без коммита

        # считаем очки
        points = await self.calculate_points(question, data.answer)

        # добавляем очки пользователю
        self.current_user.points = (self.current_user.points or 0) + points
        self.session.add(self.current_user)

        # сохраняем всё
        await self.session.commit()
        await self.session.refresh(user_answer)
        await self.session.refresh(self.current_user)

        return user_answer

    
    async def create_minigame_question(self, session: AsyncSession, data: MinigameQuestionCreate) -> MinigameQuestion:
        question = MinigameQuestion(
            text=data.text,
            options=data.options,
            correct_answers=data.correct_answers,
            points=data.points,
            minigame_id=data.minigame_id,
        )
        session.add(question)
        await session.commit()
        await session.refresh(question)
        return question
    
    async def add_question(self, data: MinigameQuestionCreate) -> dict:
        question = await self.create_minigame_question(self.session, data)
        q_type = self.get_question_type(question)
        return {
            "id": question.id,
            "text": question.text,
            "type": q_type,
            "options": question.options,
            "correct_answers": question.correct_answers,
            "points": question.points,
            "minigame_id": question.minigame_id
        }
    
    async def submit_answer(self, data: schemas.UserAnswerCreate) -> MinigameUserAnswer:
        # находим вопрос
        result = await self.session.execute(
            select(MinigameQuestion).where(MinigameQuestion.id == data.question_id)
        )
        question = result.scalar_one_or_none()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # создаём ответ
        user_answer = MinigameUserAnswer(
            user_id=self.current_user.id,
            question_id=question.id,
            minigame_id=question.minigame_id,
            answer=data.answer
        )
        self.session.add(user_answer)
        await self.session.commit()
        await self.session.refresh(user_answer)

        # считаем очки и обновляем пользователя
        points = await self.calculate_points(question, data.answer)
        self.current_user.points += points
        self.session.add(self.current_user)
        await self.session.commit()

        return user_answer
    
