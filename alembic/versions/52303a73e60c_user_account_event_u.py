"""user_account_event.user

Revision ID: 52303a73e60c
Revises: 377ecc9e43c9
Create Date: 2013-09-10 16:22:42.622635

"""

# revision identifiers, used by Alembic.
revision = '52303a73e60c'
down_revision = '377ecc9e43c9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user_account_event', sa.Column('user', sa.CHAR(length=22), nullable=True))
    op.execute('''
        update user_account_event
         set "user" = "user".id
         from "user"
         where "user".username = user_account_event.username
    ''')
    op.create_index('user_account_event_user', 'user_account_event', ['user'])


def downgrade():
    op.drop_column('user_account_event', 'user')
