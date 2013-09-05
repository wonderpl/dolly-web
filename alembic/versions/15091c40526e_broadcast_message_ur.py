"""broadcast_message.url_target

Revision ID: 15091c40526e
Revises: 2df0ad3e7d52
Create Date: 2013-09-03 15:27:07.579914

"""

# revision identifiers, used by Alembic.
revision = '15091c40526e'
down_revision = '2df0ad3e7d52'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('broadcast_message', sa.Column('url_target', sa.String(length=1024), nullable=True))


def downgrade():
    op.drop_column('broadcast_message', 'url_target')
