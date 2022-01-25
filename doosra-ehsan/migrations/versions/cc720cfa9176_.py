"""empty message

Revision ID: cc720cfa9176
Revises: e8a84a531c3d
Create Date: 2019-04-02 12:25:35.975351

"""

# revision identifiers, used by Alembic.
revision = 'cc720cfa9176'
down_revision = 'e8a84a531c3d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('gcp_clouds',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('project_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('gcp_credentials',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('token', sa.String(length=255), nullable=False),
    sa.Column('refresh_token', sa.String(length=255), nullable=True),
    sa.Column('token_uri', sa.String(length=255), nullable=True),
    sa.Column('client_id', sa.String(length=255), nullable=True),
    sa.Column('client_secret', sa.String(length=255), nullable=True),
    sa.Column('scopes', sa.Text(), nullable=True),
    sa.Column('cloud_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['cloud_id'], ['gcp_clouds.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('gcp_credentials')
    op.drop_table('gcp_clouds')
    # ### end Alembic commands ###