"""channel update frequency

Revision ID: 184815d483a3
Revises: 2d949040fe49
Create Date: 2013-04-30 18:28:30.124882

"""

# revision identifiers, used by Alembic.
revision = '184815d483a3'
down_revision = '2d949040fe49'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('channel', sa.Column('update_frequency', sa.Float(), nullable=True))
    op.execute("insert into job_control values ('update_channel_stats', '1970-01-01')")


def downgrade():
    op.drop_column('channel', 'update_frequency')
