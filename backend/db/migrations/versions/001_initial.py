"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    
    # Create resumes table
    op.create_table(
        'resumes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('parsed_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resumes_id'), 'resumes', ['id'], unique=False)
    
    # Create question_bank table
    op.create_table(
        'question_bank',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('correct_answer', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.Integer(), nullable=False),
        sa.Column('chapter', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_bank_id'), 'question_bank', ['id'], unique=False)
    
    # Create interview_sessions table
    op.create_table(
        'interview_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=True),
        sa.Column('track', sa.String(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('total_rounds', sa.Integer(), nullable=True),
        sa.Column('current_round', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interview_sessions_id'), 'interview_sessions', ['id'], unique=False)
    
    # Create interview_turns table
    op.create_table(
        'interview_turns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interview_turns_id'), 'interview_turns', ['id'], unique=False)
    
    # Create asked_questions table
    op.create_table(
        'asked_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('qbank_id', sa.String(), nullable=True),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('difficulty', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('correct_answer_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['qbank_id'], ['question_bank.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_asked_questions_id'), 'asked_questions', ['id'], unique=False)
    
    # Create evaluations table
    op.create_table(
        'evaluations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asked_question_id', sa.Integer(), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('scores_json', sa.JSON(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=False),
        sa.Column('missing_points_json', sa.JSON(), nullable=True),
        sa.Column('next_direction', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['asked_question_id'], ['asked_questions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asked_question_id')
    )
    op.create_index(op.f('ix_evaluations_id'), 'evaluations', ['id'], unique=False)
    
    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('summary_json', sa.JSON(), nullable=False),
        sa.Column('markdown', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_reports_id'), 'reports', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reports_id'), table_name='reports')
    op.drop_table('reports')
    op.drop_index(op.f('ix_evaluations_id'), table_name='evaluations')
    op.drop_table('evaluations')
    op.drop_index(op.f('ix_asked_questions_id'), table_name='asked_questions')
    op.drop_table('asked_questions')
    op.drop_index(op.f('ix_interview_turns_id'), table_name='interview_turns')
    op.drop_table('interview_turns')
    op.drop_index(op.f('ix_interview_sessions_id'), table_name='interview_sessions')
    op.drop_table('interview_sessions')
    op.drop_index(op.f('ix_question_bank_id'), table_name='question_bank')
    op.drop_table('question_bank')
    op.drop_index(op.f('ix_resumes_id'), table_name='resumes')
    op.drop_table('resumes')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')

