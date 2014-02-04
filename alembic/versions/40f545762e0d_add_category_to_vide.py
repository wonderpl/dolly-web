"""add category to Video

Revision ID: 40f545762e0d
Revises: 31e916fa941e
Create Date: 2014-02-04 16:39:56.055779

"""

# revision identifiers, used by Alembic.
revision = '40f545762e0d'
down_revision = '31e916fa941e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('video', sa.Column('category', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('video', 'category')
    ### end Alembic commands ###
