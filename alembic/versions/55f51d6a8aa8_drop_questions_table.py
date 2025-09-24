"""drop questions table

Revision ID: 55f51d6a8aa8
Revises: 46b26d814e9e
Create Date: 2025-09-24 20:13:46.567175
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '55f51d6a8aa8'
down_revision: Union[str, Sequence[str], None] = '46b26d814e9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema: drop legacy table questions."""
    # Если нужно «тихо» (без ошибки, если таблицы нет), используй raw SQL:
    op.execute("DROP TABLE IF EXISTS questions CASCADE")

def downgrade() -> None:
    """Downgrade schema: recreate table questions (схема как была)."""
    op.create_table(
        'questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('text', sa.String(length=255), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id']),
        sa.PrimaryKeyConstraint('id'),
    )
