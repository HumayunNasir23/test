"""empty message

Revision ID: b4ea8afe4805
Revises: 0e33ef5092d7
Create Date: 2020-09-22 18:50:04.603233

"""

# revision identifiers, used by Alembic.
revision = 'b4ea8afe4805'
down_revision = '0e33ef5092d7'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ibm_tokens',
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ibm_tokens')
    # ### end Alembic commands ###
