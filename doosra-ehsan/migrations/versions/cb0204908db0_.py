"""empty message

Revision ID: cb0204908db0
Revises: bf14e9db09cf
Create Date: 2020-01-19 18:46:53.390915

"""

# revision identifiers, used by Alembic.
revision = 'cb0204908db0'
down_revision = 'bf14e9db09cf'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ibm_service_credentials',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('resource_instance_id', sa.String(length=1000), nullable=False),
    sa.Column('cloud_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['cloud_id'], ['ibm_clouds.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_column('ibm_clouds', 'service_credential')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ibm_clouds', sa.Column('service_credential', mysql.VARCHAR(length=1000), nullable=True))
    op.drop_table('ibm_service_credentials')
    # ### end Alembic commands ###