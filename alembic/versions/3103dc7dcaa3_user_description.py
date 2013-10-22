"""user.description

Revision ID: 3103dc7dcaa3
Revises: 296ca64d4093
Create Date: 2013-10-18 16:14:41.232461

"""

# revision identifiers, used by Alembic.
revision = '3103dc7dcaa3'
down_revision = '296ca64d4093'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user', sa.Column('description', sa.String(length=1024), nullable=True))
    op.add_column('user', sa.Column('site_url', sa.String(length=1024), nullable=True))


def downgrade():
    op.drop_column('user', 'site_url')
    op.drop_column('user', 'description')
