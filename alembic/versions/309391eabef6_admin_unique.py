"""admin unique

Revision ID: 309391eabef6
Revises: 1bd52ae01187
Create Date: 2013-11-14 15:36:08.972940

"""

revision = '309391eabef6'
down_revision = '1bd52ae01187'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('adminuser', u'username', existing_type=sa.VARCHAR(length=254), nullable=False)
    op.create_unique_constraint('adminuser_username_uniq', 'adminuser', ['username'])
    op.alter_column('adminuser', u'email', existing_type=sa.VARCHAR(length=254), nullable=False)
    op.create_unique_constraint('adminuser_email_uniq', 'adminuser', ['email'])


def downgrade():
    op.alter_column('adminuser', u'email', existing_type=sa.VARCHAR(length=254), nullable=True)
    op.alter_column('adminuser', u'username', existing_type=sa.VARCHAR(length=254), nullable=True)
