"""Add looging failure response with status to job and job_applicant model

Revision ID: 1ea7e0c05932
Revises: 7af76c342612
Create Date: 2026-02-22 23:10:58.743223

"""
from typing import Sequence, Union

from alembic import op
import sqlmodel
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1ea7e0c05932'
down_revision: Union[str, Sequence[str], None] = '7af76c342612'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    processing_status_enum = sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='processingstatus')
    
    processing_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('job', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('job', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    op.add_column('job', sa.Column('processing_status', processing_status_enum, nullable=False, server_default='PENDING'))
    op.add_column('job', sa.Column('processing_error', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    
    op.add_column('jobapplicant', sa.Column('applied_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    
    op.add_column('jobapplicant', sa.Column('processing_status', processing_status_enum, nullable=False, server_default='PENDING'))
    op.add_column('jobapplicant', sa.Column('processing_error', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    # 1. Drop the columns first
    op.drop_column('jobapplicant', 'processing_error')
    op.drop_column('jobapplicant', 'processing_status')
    op.drop_column('jobapplicant', 'applied_at')
    op.drop_column('job', 'processing_error')
    op.drop_column('job', 'processing_status')
    op.drop_column('job', 'updated_at')
    op.drop_column('job', 'created_at')

    sa.Enum(name='processingstatus').drop(op.get_bind(), checkfirst=True)
