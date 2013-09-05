"""video_instance.source_channel

Revision ID: 21df8739c10a
Revises: 15091c40526e
Create Date: 2013-09-05 15:40:31.226611

"""

# revision identifiers, used by Alembic.
revision = '21df8739c10a'
down_revision = '15091c40526e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('video_instance', sa.Column('source_channel', sa.CHAR(length=24), nullable=True))


def downgrade():
    op.drop_column('video_instance', 'source_channel')
