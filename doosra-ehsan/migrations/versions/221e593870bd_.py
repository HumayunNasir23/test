"""empty message

Revision ID: 221e593870bd
Revises: f469f3e08b2e
Create Date: 2019-10-29 06:57:33.252854

"""

# revision identifiers, used by Alembic.
revision = '221e593870bd'
down_revision = 'f469f3e08b2e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ibm_ike_policy', sa.Column('region', sa.String(length=255), nullable=False))
    op.add_column('ibm_ipsec_policy', sa.Column('region', sa.String(length=255), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ibm_ipsec_policy', 'region')
    op.drop_column('ibm_ike_policy', 'region')
    # ### end Alembic commands ###