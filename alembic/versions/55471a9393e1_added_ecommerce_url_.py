"""added ecommerce url to channel model

Revision ID: 55471a9393e1
Revises: 597c3c38ce0f
Create Date: 2013-03-18 12:08:15.925360

"""

# revision identifiers, used by Alembic.
revision = '55471a9393e1'
down_revision = '4e5c1c08002'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('channel', sa.Column('ecommerce_url', sa.String(length=1024), nullable=False, server_default=''))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('channel', 'ecommerce_url')
    ### end Alembic commands ###
