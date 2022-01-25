"""empty message

Revision ID: 4bc0ef3c5989
Revises: bf1530701913
Create Date: 2019-06-18 10:50:43.054947

"""

# revision identifiers, used by Alembic.
revision = '4bc0ef3c5989'
down_revision = 'bf1530701913'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ibm_clouds',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('api_key', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('project_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ibm_credentials',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('access_token', sa.String(length=2000), nullable=False),
    sa.Column('refresh_token', sa.String(length=2000), nullable=True),
    sa.Column('expiration_date', sa.DateTime(), nullable=True),
    sa.Column('cloud_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['cloud_id'], ['ibm_clouds.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ibm_credentials')
    op.drop_table('ibm_clouds')
    # ### end Alembic commands ###