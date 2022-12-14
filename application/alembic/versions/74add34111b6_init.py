"""init

Revision ID: 74add34111b6
Revises: 
Create Date: 2022-09-10 22:12:50.699144

"""
from alembic import op
import sqlalchemy as sa
import datetime
import sqlalchemy_utils
from sqlalchemy import String
from database import UnitType
# UnitType, impl=String()

# revision identifiers, used by Alembic.
revision = '74add34111b6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('unit',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('date', sa.DateTime(timezone=datetime.timezone.utc), nullable=False),
    sa.Column('type', sqlalchemy_utils.types.choice.ChoiceType(UnitType, impl=String()), nullable=False),
    sa.Column('parent_id', sa.String(), nullable=True),
    sa.Column('size', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['unit.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unit_parent_id'), 'unit', ['parent_id'], unique=False)
    op.create_table('history_unit',
    sa.Column('self_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('date', sa.DateTime(timezone=datetime.timezone.utc), nullable=False),
    sa.Column('type', sqlalchemy_utils.types.choice.ChoiceType(UnitType, impl=String()), nullable=False),
    sa.Column('parent_id', sa.String(), nullable=True),
    sa.Column('size', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id'], ['unit.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('self_id', 'date')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('history_unit')
    op.drop_index(op.f('ix_unit_parent_id'), table_name='unit')
    op.drop_table('unit')
    # ### end Alembic commands ###
