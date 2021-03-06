"""new content_report table

Revision ID: 45e6dd8a6356
Revises: 57cf562ea12
Create Date: 2013-04-15 18:28:53.481742

"""

# revision identifiers, used by Alembic.
revision = '45e6dd8a6356'
down_revision = '57cf562ea12'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('content_report',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=False, index=True),
    sa.Column('object_type', sa.String(length=16), nullable=False),
    sa.Column('object_id', sa.String(length=64), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.Column('reviewed', sa.Boolean(), nullable=False, index=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('object_type','object_id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('content_report')
    ### end Alembic commands ###
