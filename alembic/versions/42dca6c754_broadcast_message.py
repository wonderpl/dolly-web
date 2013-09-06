"""broadcast_message

Revision ID: 42dca6c754
Revises: 4676bd2e1443
Create Date: 2013-08-23 16:57:19.811354

"""

# revision identifiers, used by Alembic.
revision = '42dca6c754'
down_revision = '4676bd2e1443'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


def upgrade():
    op.create_table(
        'broadcast_message',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=64), nullable=False),
        sa.Column('external_system', ENUM(name='external_system', create_type=False), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.Column('date_scheduled', sa.DateTime(), nullable=False),
        sa.Column('date_processed', sa.DateTime(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('filter', sa.String(length=1024), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('broadcast_message')
