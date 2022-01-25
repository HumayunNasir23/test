"""empty message

Revision ID: 27a9c81d0499
Revises: 7f64fd218db6
Create Date: 2020-03-28 13:03:22.677677

"""

# revision identifiers, used by Alembic.
revision = '27a9c81d0499'
down_revision = '7f64fd218db6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ibm_vpn_connections', sa.Column('discovered_local_cidrs', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ibm_vpn_connections', 'discovered_local_cidrs')
    # ### end Alembic commands ###