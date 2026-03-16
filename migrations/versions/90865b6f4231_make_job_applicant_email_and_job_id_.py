"""no-op merge revision to linearize heads after retry-count branch

Revision ID: 90865b6f4231
Revises: c3f1a8b2e905
Create Date: 2026-03-16 15:08:36.362502

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '90865b6f4231'
down_revision: Union[str, Sequence[str], None] = 'c3f1a8b2e905'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
