from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.common.db import AsyncSession, get_async_session
from app.common.common import CurrentUser
from app.users.models import User
from app.quizes import schemas
from app.quizes.models import Quiz, QuizQuestion, QuizUserAnswer
from app.quizes.schemas import QuizQuestionCreate



class QuizService:
    def __init__(self, session: AsyncSession = Depends(get_async_session), current_user: User = Depends(CurrentUser())):
        self.session = session
        self.current_user = current_user

    def get_question_type(self, question: QuizQuestion) -> str:
        if not question.correct_answers:
            return "open"
        elif len(question.correct_answers) == 1:
            return "single"
        else:
            return "multiple"

    async def calculate_points(self, question: QuizQuestion, user_answer: str | list[str]) -> int:
        q_type = self.get_question_type(question)

        if q_type == "open-ended":
            return int(user_answer.strip().lower() in (a.lower() for a in question.correct_answers))

        if q_type == "single":
            if isinstance(user_answer, list):
                if len(user_answer) != 1:
                    return 0
                user_answer = user_answer[0]
            return question.points if user_answer == question.correct_answers[0] else 0

        if q_type == "multiple":
            if not isinstance(user_answer, list):
                return 0
            correct = set(question.correct_answers)
            user_ans = set(user_answer)
            if user_ans == correct:
                return question.points
            return int(question.points * len(user_ans & correct) / len(correct))

        return 0


    async def submit_answer(self, data: schemas.UserAnswerCreate) -> QuizUserAnswer:
        # находим вопрос
        result = await self.session.execute(
            select(QuizQuestion).where(QuizQuestion.id == data.question_id)
        )
        question = result.scalar_one_or_none()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # создаём ответ
        user_answer = QuizUserAnswer(
            user_id=self.current_user.id,
            question_id=question.id,
            quiz_id=question.quiz_id,
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

        return {
            ""
        }

        return user_answer

    
    async def create_quiz_question(self, session: AsyncSession, data: QuizQuestionCreate) -> QuizQuestion:
        question = QuizQuestion(
            text=data.text,
            options=data.options,
            duration_seconds=data.duration_seconds,
            correct_answers=data.correct_answers,
            points=data.points,
            quiz_id=data.quiz_id,
        )
        session.add(question)
        await session.commit()
        await session.refresh(question)
        return question
    
    async def add_question(self, data: QuizQuestionCreate) -> dict:
        question = await self.create_quiz_question(self.session, data)
        q_type = self.get_question_type(question)
        return {
            "id": question.id,
            "text": question.text,
            "type": q_type,
            "options": question.options,
            "correct_answers": question.correct_answers,
            "points": question.points,
            "quiz_id": question.quiz_id
        }
    
    async def submit_answer(self, data: schemas.UserAnswerCreate) -> QuizUserAnswer:
        # находим вопрос
        result = await self.session.execute(
            select(QuizQuestion).where(QuizQuestion.id == data.question_id)
        )
        question = result.scalar_one_or_none()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # создаём ответ
        user_answer = QuizUserAnswer(
            user_id=self.current_user.id,
            question_id=question.id,
            quiz_id=question.quiz_id,
            answers=data.answers
        )
        self.session.add(user_answer)
        await self.session.commit()
        await self.session.refresh(user_answer)

        # считаем очки и обновляем пользователя
        points = await self.calculate_points(question, data.answers)

        self.current_user.points += points
        self.session.add(self.current_user)
        await self.session.commit()

        return user_answer
    
    async def get_quiz_questions_list(self, quiz_id: int):
        result = await self.session.execute(
            select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id)
        )
        return result.scalars().all()
    
    async def toggle_quiz_active(self, quiz_id: int, is_active: bool):
        result = await self.session.execute(
            select(Quiz).where(Quiz.quiz_id == quiz_id)
        )
        quiz = result.scalars().all()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        quiz.is_active = is_active
        self.session.add(quiz)
        await self.session.commit()
        await self.session.refresh(quiz)

        return {"id": quiz.id, "is_active": quiz.is_active}

    
