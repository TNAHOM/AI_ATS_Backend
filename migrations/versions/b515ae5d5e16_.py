"""no-op merge revision after local autogenerate produced duplicate retry_count column

Revision ID: b515ae5d5e16
Revises: 90865b6f4231
Create Date: 2026-03-16 15:55:07.011999

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b515ae5d5e16'
down_revision: Union[str, Sequence[str], None] = '90865b6f4231'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # retry_count column is already added by c3f1a8b2e905; no-op here.
    pass


def downgrade() -> None:
    pass
