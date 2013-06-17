"""player error

Revision ID: 3506499d53b3
Revises: 3e86fe829c0c
Create Date: 2013-06-17 17:48:17.151375

"""

# revision identifiers, used by Alembic.
revision = '3506499d53b3'
down_revision = '3e86fe829c0c'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column(u'content_report', sa.Column('date_updated', sa.DateTime()))
    op.execute("update content_report set date_updated = now()")
    op.alter_column('content_report', 'date_updated', nullable=False)

    op.create_table(
        'player_error',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.Column('date_updated', sa.DateTime(), nullable=False),
        sa.Column('video_instance', sa.CHAR(length=24), nullable=False),
        sa.Column('reason', sa.String(length=256), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_instance', 'reason')
    )
    op.create_index('player_error_updated', 'player_error', ['date_updated'])


def downgrade():
    op.drop_table('player_error')
    op.drop_column(u'content_report', 'date_updated')
