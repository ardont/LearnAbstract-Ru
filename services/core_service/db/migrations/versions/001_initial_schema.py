"""Initial schema for users, quiz_sessions, explanation_logs

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-27 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('max_user_id', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='GUEST_CHOICE'),
        sa.Column('interest', sa.String(length=100), nullable=True),
        sa.Column('grade', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('is_guest', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('current_quiz_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_max_user_id'), 'users', ['max_user_id'], unique=True)

    op.create_table(
        'quiz_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('quiz_id', sa.String(length=100), nullable=False),
        sa.Column('max_user_id', sa.String(length=100), nullable=False),
        sa.Column('topic', sa.String(length=200), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('options_json', sa.Text(), nullable=False),
        sa.Column('correct_option_index', sa.Integer(), nullable=False),
        sa.Column('user_answer', sa.Integer(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('answered_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_sessions_quiz_id'), 'quiz_sessions', ['quiz_id'], unique=True)
    op.create_index(op.f('ix_quiz_sessions_max_user_id'), 'quiz_sessions', ['max_user_id'], unique=False)

    op.create_table(
        'explanation_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('max_user_id', sa.String(length=100), nullable=False),
        sa.Column('topic', sa.String(length=200), nullable=False),
        sa.Column('interest', sa.String(length=100), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='llm'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_guest', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_explanation_logs_max_user_id'), 'explanation_logs', ['max_user_id'], unique=False)

def downgrade() -> None:
    op.drop_table('explanation_logs')
    op.drop_table('quiz_sessions')
    op.drop_table('users')
