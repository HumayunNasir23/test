"""empty message

Revision ID: e347ec8bfc75
Revises: 935eae637a37
Create Date: 2020-06-07 11:31:30.812043

"""

# revision identifiers, used by Alembic.
revision = 'e347ec8bfc75'
down_revision = '935eae637a37'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('ibm_clouds', 'api_key',
                    existing_type=mysql.VARCHAR(length=255),
                    type_=mysql.VARCHAR(length=500),
                    existing_nullable=False)
    op.alter_column('softlayer_clouds', 'api_key',
                    existing_type=mysql.VARCHAR(length=255),
                    type_=mysql.VARCHAR(length=500),
                    existing_nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('ibm_clouds', 'api_key',
                    existing_type=mysql.VARCHAR(length=500),
                    type_=mysql.VARCHAR(length=255),
                    existing_nullable=False)
    op.alter_column('softlayer_clouds', 'api_key',
                    existing_type=mysql.VARCHAR(length=500),
                    type_=mysql.VARCHAR(length=255),
                    existing_nullable=False)
    # ### end Alembic commands ###