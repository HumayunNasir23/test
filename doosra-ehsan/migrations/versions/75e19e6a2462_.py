"""empty message

Revision ID: 75e19e6a2462
Revises: da2be34131a8
Create Date: 2019-07-16 10:39:33.179191

"""

# revision identifiers, used by Alembic.
revision = '75e19e6a2462'
down_revision = 'da2be34131a8'

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ibm_public_gateways', sa.Column('cloud_id', sa.String(length=32), nullable=False))
    op.add_column('ibm_public_gateways', sa.Column('status', sa.String(length=50), nullable=False))
    op.add_column('ibm_public_gateways', sa.Column('vpc_id', sa.String(length=32), nullable=False))
    op.create_foreign_key('ibm_public_gateways_clouds_ibfk_1', 'ibm_public_gateways', 'ibm_clouds', ['cloud_id'], ['id'])
    op.create_foreign_key('ibm_public_gateways_vpcs_ibfk_2', 'ibm_public_gateways', 'ibm_vpc_networks', ['vpc_id'], ['id'])
    op.add_column('ibm_subnets', sa.Column('public_gateway_id', sa.String(length=32), nullable=True))
    op.create_foreign_key('ibm_public_gateways_subnets_ibfk_3', 'ibm_subnets', 'ibm_public_gateways', ['public_gateway_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('ibm_public_gateways_subnets_ibfk_3', 'ibm_subnets', type_='foreignkey')
    op.drop_column('ibm_subnets', 'public_gateway_id')
    op.drop_constraint('ibm_public_gateways_vpcs_ibfk_2', 'ibm_public_gateways', type_='foreignkey')
    op.drop_constraint('ibm_public_gateways_clouds_ibfk_1', 'ibm_public_gateways', type_='foreignkey')
    op.drop_column('ibm_public_gateways', 'vpc_id')
    op.drop_column('ibm_public_gateways', 'status')
    op.drop_column('ibm_public_gateways', 'cloud_id')
    # ### end Alembic commands ###
