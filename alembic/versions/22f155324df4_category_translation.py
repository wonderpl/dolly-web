"""category translation

Revision ID: 22f155324df4
Revises: 57cf562ea12
Create Date: 2013-04-15 19:28:36.259451

"""

# revision identifiers, used by Alembic.
revision = '22f155324df4'
down_revision = '57cf562ea12'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('category_translation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('locale', sa.String(length=16), nullable=False),
    sa.Column('category', sa.Integer(), nullable=False),
    sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
    sa.Column('name', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['category'], ['category.id'], ),
    sa.ForeignKeyConstraint(['locale'], ['locale.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('locale','category','name')
    )
    op.execute("insert into category_translation (category, name, locale, priority) select id, name, locale, priority from category where locale = 'en-us'")
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('category_translation')
    ### end Alembic commands ###
