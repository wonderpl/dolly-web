"""user_flag

Revision ID: 29f888125052
Revises: 1f497db49261
Create Date: 2013-08-02 12:08:11.328155

"""

# revision identifiers, used by Alembic.
revision = '29f888125052'
down_revision = '1f497db49261'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'user_flag',
        sa.Column('user', sa.CHAR(length=22), nullable=False),
        sa.Column('flag', sa.Enum('facebook_autopost_star', 'facebook_autopost_add', name='user_flag_enum'), nullable=False),
        sa.ForeignKeyConstraint(['user'], ['user.id'], ),
        sa.PrimaryKeyConstraint('user', 'flag')
    )


def downgrade():
    op.drop_table('user_flag')
    op.execute('drop type user_flag_enum')
