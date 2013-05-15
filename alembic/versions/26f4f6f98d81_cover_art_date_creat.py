"""cover_art date_created

Revision ID: 26f4f6f98d81
Revises: 32f0a39a1bb9
Create Date: 2013-05-15 16:35:54.356642

"""

# revision identifiers, used by Alembic.
revision = '26f4f6f98d81'
down_revision = '32f0a39a1bb9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('rockpack_cover_art', sa.Column('date_created', sa.DateTime(), nullable=False, server_default='now()'))
    op.create_index('rockpack_cover_art_date_created', 'rockpack_cover_art', ['date_created'])
    op.add_column('user_cover_art', sa.Column('date_created', sa.DateTime(), nullable=False, server_default='now()'))
    op.create_index('user_cover_art_date_created', 'user_cover_art', ['date_created'])
    op.create_foreign_key('user_cover_art_owner_fkey', 'user_cover_art', 'user', ['owner'], ['id'])


def downgrade():
    op.drop_column('user_cover_art', 'date_created')
    op.drop_column('rockpack_cover_art', 'date_created')
