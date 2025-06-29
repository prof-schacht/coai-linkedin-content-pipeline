"""Add LinkedIn connections and expertise mapping tables

Revision ID: 6505841ea2a6
Revises: 8cbe8fd8d641
Create Date: 2025-05-29 09:06:52.383066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6505841ea2a6'
down_revision: Union[str, None] = '8cbe8fd8d641'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('expertise_mappings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('expertise_area', sa.String(length=50), nullable=False),
    sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('weight', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expertise_mappings_expertise_area'), 'expertise_mappings', ['expertise_area'], unique=False)
    op.create_table('linkedin_connections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('connection_hash', sa.String(length=64), nullable=False),
    sa.Column('full_name', sa.Text(), nullable=False),
    sa.Column('company', sa.Text(), nullable=True),
    sa.Column('position', sa.Text(), nullable=True),
    sa.Column('location', sa.Text(), nullable=True),
    sa.Column('connected_date', sa.Date(), nullable=True),
    sa.Column('expertise_tags', sa.ARRAY(sa.String()), nullable=True),
    sa.Column('ai_safety_score', sa.Float(), nullable=True),
    sa.Column('interview_potential_score', sa.Float(), nullable=True),
    sa.Column('mention_relevance_score', sa.Float(), nullable=True),
    sa.Column('connection_degree', sa.Integer(), nullable=True),
    sa.Column('mutual_connections', sa.Integer(), nullable=True),
    sa.Column('is_verified_expert', sa.Boolean(), nullable=True),
    sa.Column('matched_author_names', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('matched_social_handles', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('posts_about_ai', sa.Integer(), nullable=True),
    sa.Column('last_mentioned_date', sa.Date(), nullable=True),
    sa.Column('mention_count', sa.Integer(), nullable=True),
    sa.Column('last_analyzed', sa.DateTime(), nullable=True),
    sa.Column('excluded_from_analysis', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_linkedin_company_position', 'linkedin_connections', ['company', 'position'], unique=False)
    op.create_index('idx_linkedin_expertise_scores', 'linkedin_connections', ['ai_safety_score', 'interview_potential_score'], unique=False)
    op.create_index('idx_linkedin_expertise_tags', 'linkedin_connections', ['expertise_tags'], unique=False, postgresql_using='gin')
    op.create_index(op.f('ix_linkedin_connections_ai_safety_score'), 'linkedin_connections', ['ai_safety_score'], unique=False)
    op.create_index(op.f('ix_linkedin_connections_connection_hash'), 'linkedin_connections', ['connection_hash'], unique=True)
    op.create_index(op.f('ix_linkedin_connections_interview_potential_score'), 'linkedin_connections', ['interview_potential_score'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_linkedin_connections_interview_potential_score'), table_name='linkedin_connections')
    op.drop_index(op.f('ix_linkedin_connections_connection_hash'), table_name='linkedin_connections')
    op.drop_index(op.f('ix_linkedin_connections_ai_safety_score'), table_name='linkedin_connections')
    op.drop_index('idx_linkedin_expertise_tags', table_name='linkedin_connections', postgresql_using='gin')
    op.drop_index('idx_linkedin_expertise_scores', table_name='linkedin_connections')
    op.drop_index('idx_linkedin_company_position', table_name='linkedin_connections')
    op.drop_table('linkedin_connections')
    op.drop_index(op.f('ix_expertise_mappings_expertise_area'), table_name='expertise_mappings')
    op.drop_table('expertise_mappings')
    # ### end Alembic commands ###
