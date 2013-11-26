"""feedback_record

Revision ID: 2b0c3f05d150
Revises: f4c98b9a67f
Create Date: 2013-11-25 18:09:49.645107

"""

# revision identifiers, used by Alembic.
revision = '2b0c3f05d150'
down_revision = 'f4c98b9a67f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'feedback_record',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date_added', sa.DateTime(), nullable=False),
        sa.Column('user', sa.CHAR(length=22), nullable=False),
        sa.Column('message', sa.String(length=1024), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('feedback_record_date_added_idx', 'feedback_record', ['date_added'])
    op.create_index('feedback_record_user_idx', 'feedback_record', ['user'])


def downgrade():
    op.drop_table('feedback_record')
