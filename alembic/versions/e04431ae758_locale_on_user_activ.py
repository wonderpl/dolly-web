"""locale on user_activity

Revision ID: e04431ae758
Revises: 25c5da6174ee
Create Date: 2013-06-19 17:04:29.273196

"""

# revision identifiers, used by Alembic.
revision = 'e04431ae758'
down_revision = '3b4ae8f1d5bd'

from alembic import op
import sqlalchemy as sa

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_activity', sa.Column('locale', sa.String(length=16), server_default='en-us', nullable=False))
    op.create_index('locale_index', 'user_activity', ['locale'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user_activity', 'locale')
    ### end Alembic commands ###
