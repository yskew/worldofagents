"""add HNSW cosine index on agents.signature_vector (RFC 0005)

Enables fast approximate nearest-neighbour search for the /similar endpoint.
HNSW needs no training step (unlike ivfflat) and supports incremental inserts,
so it is safe to create on a populated or empty table. Exact KNN still works
without the index; this only accelerates it.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-09 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agents_signature_vector_hnsw "
        "ON agents USING hnsw (signature_vector vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_agents_signature_vector_hnsw")
