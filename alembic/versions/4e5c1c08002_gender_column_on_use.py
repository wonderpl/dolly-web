"""gender column on User

Revision ID: 4e5c1c08002
Revises: 597c3c38ce0f
Create Date: 2013-03-28 15:56:47.413151

"""

# revision identifiers, used by Alembic.
revision = '4e5c1c08002'
down_revision = '597c3c38ce0f'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.execute("CREATE TYPE gender_enum AS ENUM ('m', 'f')")
    op.add_column('user',
            sa.Column('gender', sa.Enum('m', 'f', name='gender_enum'), nullable=True))


def downgrade():
    op.drop_column('user', 'gender')
