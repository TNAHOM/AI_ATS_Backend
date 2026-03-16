"""Add retry_count column and DEAD_LETTER application status

Revision ID: c3f1a8b2e905
Revises: 1ea7e0c05932
Create Date: 2026-03-16 07:50:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f1a8b2e905"
down_revision: Union[str, Sequence[str], None] = "1ea7e0c05932"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add DEAD_LETTER to the applicationstatus enum.
    #    PostgreSQL requires a raw DDL statement for this; it cannot be done
    #    via the ORM or op.alter_column().
    op.execute("ALTER TYPE applicationstatus ADD VALUE IF NOT EXISTS 'DEAD_LETTER'")

    # 2. Add retry_count column to jobapplicant table.
    op.add_column(
        "jobapplicant",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    # Remove the retry_count column.
    op.drop_column("jobapplicant", "retry_count")

    # NOTE: PostgreSQL does not support removing values from an existing enum
    # type in-place.  To fully revert the DEAD_LETTER value you would need to:
    #   1. Create a new enum without DEAD_LETTER.
    #   2. Migrate the column to use the new enum (casting rows if needed).
    #   3. Drop the old enum and rename the new one.
    # This is intentionally left as a no-op to avoid destructive data loss on
    # downgrade; the extra enum value is harmless when unused.
