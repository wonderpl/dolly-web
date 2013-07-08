"""external friend

Revision ID: 2a1b3809d376
Revises: 435343b23cef
Create Date: 2013-07-08 17:33:46.348715

"""

# revision identifiers, used by Alembic.
revision = '2a1b3809d376'
down_revision = '435343b23cef'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


def upgrade():
    op.create_table(
        'external_friend',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user', sa.CHAR(length=22), nullable=False),
        sa.Column('external_system', ENUM(name='external_system_names', create_type=False), nullable=False),
        sa.Column('external_uid', sa.String(length=1024), nullable=False),
        sa.Column('date_updated', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=1024), nullable=False),
        sa.Column('avatar_url', sa.String(length=1024), nullable=False),
        sa.Column('has_ios_device', sa.Boolean()),
        sa.ForeignKeyConstraint(['user'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('external_friend_user', 'external_friend', ['user'])
    op.create_index('external_friend_uid', 'external_friend', ['external_system', 'external_uid'])


def downgrade():
    op.drop_table('external_friend')
