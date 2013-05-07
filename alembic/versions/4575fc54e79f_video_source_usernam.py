"""video source_username

Revision ID: 4575fc54e79f
Revises: 125a8d23c35
Create Date: 2013-05-07 21:20:35.441190

"""

# revision identifiers, used by Alembic.
revision = '4575fc54e79f'
down_revision = '125a8d23c35'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('video', sa.Column('source_username', sa.String(length=128), nullable=True, server_default=''))


def downgrade():
    op.drop_column('video', 'source_username')
