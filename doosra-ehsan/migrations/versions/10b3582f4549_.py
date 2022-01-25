"""empty message

Revision ID: 10b3582f4549
Revises: 75e19e6a2462
Create Date: 2019-07-17 09:44:59.060699

"""

# revision identifiers, used by Alembic.
revision = '10b3582f4549'
down_revision = '75e19e6a2462'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ibm_floating_ips',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('resource_id', sa.String(length=64), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('zone', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('cloud_id', sa.String(length=32), nullable=False),
    sa.Column('public_gateway_id', sa.String(length=32), nullable=True),
    sa.ForeignKeyConstraint(['cloud_id'], ['ibm_clouds.id'], ),
    sa.ForeignKeyConstraint(['public_gateway_id'], ['ibm_public_gateways.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ibm_floating_ips')
    # ### end Alembic commands ###