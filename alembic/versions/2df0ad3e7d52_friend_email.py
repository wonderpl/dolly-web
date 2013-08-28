"""friend email

Revision ID: 2df0ad3e7d52
Revises: 42dca6c754
Create Date: 2013-08-28 12:11:45.834053

"""

# revision identifiers, used by Alembic.
revision = '2df0ad3e7d52'
down_revision = '42dca6c754'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('external_friend', sa.Column('email', sa.String(length=254), nullable=True))
    op.add_column('external_friend', sa.Column('last_shared_date', sa.DateTime(), nullable=True))
    op.alter_column('external_friend', u'name', existing_type=sa.VARCHAR(length=1024), nullable=True)
    op.alter_column('external_friend', u'avatar_url', existing_type=sa.VARCHAR(length=1024), nullable=True)


def downgrade():
    op.alter_column('external_friend', u'avatar_url', existing_type=sa.VARCHAR(length=1024), nullable=False)
    op.alter_column('external_friend', u'name', existing_type=sa.VARCHAR(length=1024), nullable=False)
    op.drop_column('external_friend', 'last_shared_date')
    op.drop_column('external_friend', 'email')
