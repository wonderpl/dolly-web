"""video.date_published

Revision ID: 3e86fe829c0c
Revises: 19d6977182de
Create Date: 2013-06-06 16:00:26.552767

"""

# revision identifiers, used by Alembic.
revision = '3e86fe829c0c'
down_revision = '19d6977182de'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('video', sa.Column('date_published', sa.DateTime()))
    op.execute("update video set date_published = date_added - random() * interval '1 minute'")
    op.alter_column('video', 'date_published', nullable=False)


def downgrade():
    op.drop_column('video', 'date_published')
