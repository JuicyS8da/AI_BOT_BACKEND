"""add event_id to quizes

Revision ID: ee75bbeac664
Revises: 55f51d6a8aa8
Create Date: 2025-09-24 20:41:14.013085

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee75bbeac664'
down_revision: Union[str, Sequence[str], None] = '55f51d6a8aa8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) добавляем колонку как NULLABLE, чтобы не упасть на данных
    op.add_column(
        "quizes",
        sa.Column("event_id", sa.Integer(), nullable=True)
    )
    # 2) вешаем FK
    op.create_foreign_key(
        "quizes_event_fkey",
        "quizes", "events",
        ["event_id"], ["id"],
        ondelete="CASCADE"
    )
    # 3) (опционально) если хочешь сразу сделать NOT NULL и знаешь чем заполнить:
    # op.execute("UPDATE quizes SET event_id = 1 WHERE event_id IS NULL")  # пример
    # op.alter_column("quizes", "event_id", nullable=False)

def downgrade() -> None:
    op.drop_constraint("quizes_event_fkey", "quizes", type_="foreignkey")
    op.drop_column("quizes", "event_id")