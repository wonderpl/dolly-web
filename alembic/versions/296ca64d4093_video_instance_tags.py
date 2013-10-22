"""video_instance.tags

Revision ID: 296ca64d4093
Revises: 48e2b79a98b4
Create Date: 2013-10-16 12:24:14.526267

"""

# revision identifiers, used by Alembic.
revision = '296ca64d4093'
down_revision = '48e2b79a98b4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('video_instance', sa.Column('tags', sa.String(length=1024), nullable=True))


def downgrade():
    op.drop_column('video_instance', 'tags')
