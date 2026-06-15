"""add score_version to verification_log (RFC 0001)

Adds a nullable provenance column recording which scoring regime produced each
verification's similarity_score. Nullable + additive, so it is safe on existing
rows (they remain NULL, interpreted as pre-RFC / legacy).

Revision ID: a1b2c3d4e5f6
Revises: 012117a4a32b
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '012117a4a32b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'verification_log',
        sa.Column('score_version', sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('verification_log', 'score_version')
