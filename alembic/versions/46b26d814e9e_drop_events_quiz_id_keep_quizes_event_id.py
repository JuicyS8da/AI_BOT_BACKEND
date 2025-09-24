"""drop events.quiz_id (keep quizes.event_id)

Revision ID: 46b26d814e9e
Revises: dd5cb1aa9570
Create Date: 2025-09-24 19:35:44.690653

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "46b26d814e9e"
down_revision = "183714bcb3ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
