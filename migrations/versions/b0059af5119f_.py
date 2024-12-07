"""empty message

Revision ID: b0059af5119f
Revises: 589cbe5d3ebc
Create Date: 2024-05-24 20:53:25.734729

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b0059af5119f'
down_revision = '589cbe5d3ebc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_index('ix_matches_played_at')
        batch_op.create_index(batch_op.f('ix_matches_played_at'), ['played_at'], unique=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_matches_played_at'))
        batch_op.create_index('ix_matches_played_at', ['played_at'], unique=False)

    # ### end Alembic commands ###