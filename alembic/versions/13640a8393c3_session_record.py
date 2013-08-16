"""session_record

Revision ID: 13640a8393c3
Revises: 29f888125052
Create Date: 2013-08-15 23:14:24.065712

"""

# revision identifiers, used by Alembic.
revision = '13640a8393c3'
down_revision = '29f888125052'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'session_record',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_date', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(length=32), nullable=False),
        sa.Column('user_agent', sa.String(length=1024), nullable=False),
        sa.Column('user', sa.CHAR(length=22), nullable=True),
        sa.Column('value', sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('session_record')
