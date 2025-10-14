"""Add answer_limit to quizes

Revision ID: 2fd7df7286a6
Revises: 
Create Date: 2025-10-15 04:56:23.522736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2fd7df7286a6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quizes", sa.Column("answer_limit", sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column("quizes", "answer_limit")