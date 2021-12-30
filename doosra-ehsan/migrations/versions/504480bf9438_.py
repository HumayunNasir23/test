"""empty message

Revision ID: 504480bf9438
Revises: 40dc591aa07b
Create Date: 2019-09-05 10:20:59.692516

"""

# revision identifiers, used by Alembic.
revision = '504480bf9438'
down_revision = '40dc591aa07b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ibm_floating_ips', sa.Column('region', sa.String(length=255), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ibm_floating_ips', 'region')
    # ### end Alembic commands ###