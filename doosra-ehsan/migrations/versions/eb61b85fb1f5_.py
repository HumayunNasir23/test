"""empty message

Revision ID: eb61b85fb1f5
Revises: 2ce998b4b593
Create Date: 2019-04-30 14:41:11.621695

"""

# revision identifiers, used by Alembic.
revision = 'eb61b85fb1f5'
down_revision = '2ce998b4b593'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('gcp_tags',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('tag', sa.String(length=255), nullable=False),
    sa.Column('vpc_network_id', sa.String(length=32), nullable=True),
    sa.ForeignKeyConstraint(['vpc_network_id'], ['gcp_vpc_networks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('gcp_instance_tags',
    sa.Column('tag_id', sa.String(length=32), nullable=False),
    sa.Column('instance_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['instance_id'], ['gcp_instances.id'], ),
    sa.ForeignKeyConstraint(['tag_id'], ['gcp_tags.id'], ),
    sa.PrimaryKeyConstraint('tag_id', 'instance_id')
    )
    op.add_column('gcp_network_interfaces', sa.Column('sub_network_id', sa.String(length=32), nullable=False))
    op.add_column('gcp_network_interfaces', sa.Column('vpc_network_id', sa.String(length=32), nullable=False))
    op.create_foreign_key('gcp_network_interfaces_ibfk_2', 'gcp_network_interfaces', 'gcp_subnets', ['sub_network_id'], ['id'])
    op.create_foreign_key('gcp_network_interfaces_ibfk_3', 'gcp_network_interfaces', 'gcp_vpc_networks', ['vpc_network_id'], ['id'])
    op.drop_column('gcp_network_interfaces', 'network')
    op.drop_column('gcp_network_interfaces', 'sub_network')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('gcp_network_interfaces', sa.Column('sub_network', mysql.VARCHAR(length=255), nullable=True))
    op.add_column('gcp_network_interfaces', sa.Column('network', mysql.VARCHAR(length=255), nullable=True))
    op.drop_constraint('gcp_network_interfaces_ibfk_3', 'gcp_network_interfaces', type_='foreignkey')
    op.drop_constraint('gcp_network_interfaces_ibfk_2', 'gcp_network_interfaces', type_='foreignkey')
    op.drop_column('gcp_network_interfaces', 'vpc_network_id')
    op.drop_column('gcp_network_interfaces', 'sub_network_id')
    op.drop_table('gcp_instance_tags')
    op.drop_table('gcp_tags')
    # ### end Alembic commands ###