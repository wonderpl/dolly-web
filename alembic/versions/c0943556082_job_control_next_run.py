"""job_control.next_run

Revision ID: c0943556082
Revises: 3ed488e071a4
Create Date: 2014-05-16 16:03:16.932046

"""

# revision identifiers, used by Alembic.
revision = 'c0943556082'
down_revision = '3ed488e071a4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('job_control', sa.Column('next_run', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('job_control', 'next_run')
