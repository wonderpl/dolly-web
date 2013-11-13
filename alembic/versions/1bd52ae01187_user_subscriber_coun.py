"""user.subscriber_count

Revision ID: 1bd52ae01187
Revises: 2872f85c3170
Create Date: 2013-11-13 10:52:50.899629

"""

# revision identifiers, used by Alembic.
revision = '1bd52ae01187'
down_revision = '2872f85c3170'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user', sa.Column('subscriber_count', sa.Integer(), server_default='0', nullable=False))


def downgrade():
    op.drop_column('user', 'subscriber_count')
