"""add tool_allowlist to agents (RFC 0012)

MCP tools an agent may call. Nullable + additive; NULL means no tools authorized.

Revision ID: f1a2b3c4d5e6
Revises: 012117a4a32b
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = '012117a4a32b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'agents',
        sa.Column('tool_allowlist', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('agents', 'tool_allowlist')
