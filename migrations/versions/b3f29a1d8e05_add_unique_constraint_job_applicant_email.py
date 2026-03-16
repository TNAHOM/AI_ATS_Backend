"""Add unique constraint on (job_post_id, email) in jobapplicant table

Revision ID: b3f29a1d8e05
Revises: 1ea7e0c05932
Create Date: 2026-03-16 07:50:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f29a1d8e05"
down_revision: Union[str, Sequence[str], None] = "1ea7e0c05932"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_job_applicant_job_post_email",
        "jobapplicant",
        ["job_post_id", "email"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_job_applicant_job_post_email",
        "jobapplicant",
        type_="unique",
    )
