"""video_instance.original_channel_owner

Revision ID: 834ff2d187
Revises: 22ea09f8a62b
Create Date: 2014-04-01 14:18:28.853319

"""

# revision identifiers, used by Alembic.
revision = '834ff2d187'
down_revision = '22ea09f8a62b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('video_instance', sa.Column('original_channel_owner', sa.CHAR(length=22), nullable=True))


def downgrade():
    op.drop_column('video_instance', 'original_channel_owner')
