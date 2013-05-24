"""drop unique constraint on channel

Revision ID: 19d6977182de
Revises: 26f4f6f98d81
Create Date: 2013-05-24 10:47:52.636477

"""

# revision identifiers, used by Alembic.
revision = '19d6977182de'
down_revision = '26f4f6f98d81'

from alembic import op

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.execute('ALTER TABLE channel DROP CONSTRAINT channel_owner_title_key')
    ### end Alembic commands ###


def downgrade():
    op.execute('ALTER TABLE channel ADD CONSTRAINT channel_owner_title_key UNIQUE (owner, title)')
    ### end Alembic commands ###