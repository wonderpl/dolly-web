"""channel date_published

Revision ID: 2465166e851f
Revises: 2a1b3809d376
Create Date: 2013-07-23 14:53:40.067843

"""

# revision identifiers, used by Alembic.
revision = '2465166e851f'
down_revision = '2a1b3809d376'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('channel', sa.Column('date_published', sa.DateTime(), nullable=True))
    op.execute('update channel set date_published = date_added where public = true')


def downgrade():
    op.drop_column('channel', 'date_published')
