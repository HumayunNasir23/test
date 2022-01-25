"""empty message

Revision ID: a30ef4b6c469
Revises: a08aa65c7816
Create Date: 2019-12-19 15:31:40.074440

"""

# revision identifiers, used by Alembic.
revision = 'a30ef4b6c469'
down_revision = 'a08aa65c7816'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('private_key', sa.String(length=2000), nullable=True))
    op.add_column('users', sa.Column('public_key', sa.String(length=500), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'public_key')
    op.drop_column('users', 'private_key')
    # ### end Alembic commands ###