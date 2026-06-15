"""add signature_version to agents (RFC 0002)

Records which vector encoding produced agents.signature_vector. Nullable +
additive, safe on existing rows (NULL = legacy encoding). The re-embedding
backfill (scripts/reembed.py) stamps this when it recomputes vectors.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'agents',
        sa.Column('signature_version', sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('agents', 'signature_version')
