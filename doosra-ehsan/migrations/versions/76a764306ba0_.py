"""empty message

Revision ID: 76a764306ba0
Revises: 4bc0ef3c5989
Create Date: 2019-07-08 12:23:26.021030

"""

# revision identifiers, used by Alembic.
revision = '76a764306ba0'
down_revision = '4bc0ef3c5989'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ibm_public_gateways',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('zone', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ibm_network_acls',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('region', sa.String(length=50), nullable=True),
    sa.Column('cloud_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['cloud_id'], ['ibm_clouds.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ibm_resource_groups',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('cloud_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['cloud_id'], ['ibm_clouds.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ibm_tasks',
    sa.Column('id', sa.String(length=100), nullable=False),
    sa.Column('type', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('action', sa.String(length=32), nullable=False),
    sa.Column('region', sa.String(length=32), nullable=True),
    sa.Column('result', sa.Text(), nullable=True),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('message', sa.String(length=500), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('cloud_id', sa.String(length=32), nullable=True),
    sa.ForeignKeyConstraint(['cloud_id'], ['ibm_clouds.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ibm_network_acl_rules',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('action', sa.String(length=255), nullable=False),
    sa.Column('protocol', sa.String(length=255), nullable=False),
    sa.Column('direction', sa.String(length=255), nullable=False),
    sa.Column('destination', sa.String(length=255), nullable=True),
    sa.Column('source', sa.String(length=255), nullable=True),
    sa.Column('port_max', sa.Integer(), nullable=True),
    sa.Column('port_min', sa.Integer(), nullable=True),
    sa.Column('source_port_max', sa.Integer(), nullable=True),
    sa.Column('source_port_min', sa.Integer(), nullable=True),
    sa.Column('code', sa.Integer(), nullable=True),
    sa.Column('type', sa.Integer(), nullable=True),
    sa.Column('acl_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['acl_id'], ['ibm_network_acls.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ibm_vpc_networks',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('region', sa.String(length=255), nullable=False),
    sa.Column('classic_access', sa.Boolean(), nullable=False),
    sa.Column('cloud_id', sa.String(length=32), nullable=False),
    sa.Column('resource_group_id', sa.String(length=32), nullable=True),
    sa.Column('network_acl_id', sa.String(length=32), nullable=True),
    sa.ForeignKeyConstraint(['cloud_id'], ['ibm_clouds.id'], ),
    sa.ForeignKeyConstraint(['network_acl_id'], ['ibm_network_acls.id'], ),
    sa.ForeignKeyConstraint(['resource_group_id'], ['ibm_resource_groups.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ibm_security_groups',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('vpc_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['vpc_id'], ['ibm_vpc_networks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ibm_subnets',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('zone', sa.String(length=255), nullable=False),
    sa.Column('ipv4_cidr_block', sa.String(length=255), nullable=False),
    sa.Column('vpc_id', sa.String(length=32), nullable=False),
    sa.Column('network_acl_id', sa.String(length=32), nullable=True),
    sa.ForeignKeyConstraint(['network_acl_id'], ['ibm_network_acls.id'], ),
    sa.ForeignKeyConstraint(['vpc_id'], ['ibm_vpc_networks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ibm_security_group_rules',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('direction', sa.String(length=255), nullable=False),
    sa.Column('rule_type', sa.String(length=255), nullable=True),
    sa.Column('protocol', sa.String(length=255), nullable=True),
    sa.Column('cidr_block', sa.String(length=255), nullable=True),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('port_max', sa.String(length=255), nullable=True),
    sa.Column('port_min', sa.String(length=255), nullable=True),
    sa.Column('code', sa.String(length=255), nullable=True),
    sa.Column('type', sa.String(length=255), nullable=True),
    sa.Column('security_group_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['security_group_id'], ['ibm_security_groups.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ibm_security_group_rules')
    op.drop_table('ibm_subnets')
    op.drop_table('ibm_security_groups')
    op.drop_table('ibm_vpc_networks')
    op.drop_table('ibm_network_acl_rules')
    op.drop_table('ibm_tasks')
    op.drop_table('ibm_resource_groups')
    op.drop_table('ibm_network_acls')
    op.drop_table('ibm_public_gateways')
    # ### end Alembic commands ###