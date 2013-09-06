"""user_flag_enum

Revision ID: 377ecc9e43c9
Revises: 21df8739c10a
Create Date: 2013-09-05 18:01:40.388019

"""

# revision identifiers, used by Alembic.
revision = '377ecc9e43c9'
down_revision = '21df8739c10a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # can't update type in transaction :-(
    print 'X' * 80
    print 'Apply manually:'
    for i in range(1, 5):
        print "alter type user_flag_enum add value 'unsub%d';" % i
    print "alter type user_flag_enum add value 'bouncing';"


def downgrade():
    # can't remove value from enum type :-(
    pass
