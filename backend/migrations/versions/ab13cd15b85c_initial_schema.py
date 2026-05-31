"""initial schema — barcha jadvallar va cheklovlar (task 2.2)

Ushbu boshlang'ich migratsiya butun MVP sxemasini yaratadi (`design.md` —
"Data Models"). U `app.models.base.Base.metadata` dan avtomatik generatsiya
qilingan va quyidagi cheklovlarni o'z ichiga oladi:

- CHECK: ``users.experience_years`` 0..60 (R5.3); ``tests.duration_minutes``
  1..600 (R14.2); ``tests.category`` whitelisti (R6.2); ``questions.score``
  0.01..1000 (R14.3); ``test_results.percentage`` va
  ``competency_results.percentage`` 0..100 (R8.1, R8.8); ``expert_reviews``
  har bir mezon 1..5 (R13.1); ``feedbacks.source_type`` whitelisti (R18.1).
- UNIQUE: ``users.phone`` (R1.6, R5.4); ``roles.name``;
  ``test_results.session_id`` (idempotentlik, R7.7).
- Qisman noyob indeks: ``test_sessions`` UNIQUE (user_id, test_id)
  WHERE status='in_progress' (R7.10).
- Barcha FK referensial cheklovlar (R14.8).

Eslatma (qo'lda kiritilgan tuzatishlar):
- ``created_at`` ustunlari uchun ``server_default`` PostgreSQL ``now()`` sifatida
  beriladi (model ``func.now()`` ga mos; design "TIMESTAMPTZ DEFAULT now()").
- ``feedbacks.payload`` JSONB ``astext_type`` ``sa.Text()`` bilan to'g'ri
  ko'rsatilgan (autogenerate'ning bo'sh ``Text()`` havolasi tuzatildi).
- Qisman noyob indeks oddiy ``op.create_index`` orqali yaratiladi
  (``postgresql_where`` + ``sqlite_where`` — har ikki backend uchun).

Revision ID: ab13cd15b85c
Revises:
Create Date: 2026-05-30 20:34:18.664449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ab13cd15b85c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'competencies',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_competencies')),
    )
    op.create_table(
        'files',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('storage_key', sa.Text(), nullable=False),
        sa.Column('file_url', sa.Text(), nullable=True),
        sa.Column('file_type', sa.String(length=10), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_files')),
    )
    op.create_table(
        'regions',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_regions')),
    )
    op.create_table(
        'roles',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
        sa.UniqueConstraint('name', name=op.f('uq_roles_name')),
    )
    op.create_table(
        'tests',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=40), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("category IN ('kognitiv', 'kompetensiya', 'reflexiv', 'situatsion')", name=op.f('ck_tests_category_valid')),
        sa.CheckConstraint('duration_minutes >= 1 AND duration_minutes <= 600', name=op.f('ck_tests_duration_minutes_range')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tests')),
    )
    op.create_table(
        'token_blacklist',
        sa.Column('jti', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('jti', name=op.f('pk_token_blacklist')),
    )
    op.create_table(
        'organizations',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('region_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('org_type', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['region_id'], ['regions.id'], name=op.f('fk_organizations_region_id_regions')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_organizations')),
    )
    op.create_table(
        'questions',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('test_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('competency_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('question_text', sa.String(length=1000), nullable=False),
        sa.Column('question_type', sa.String(length=20), nullable=True),
        sa.Column('score', sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('score >= 0.01 AND score <= 1000', name=op.f('ck_questions_score_range')),
        sa.ForeignKeyConstraint(['competency_id'], ['competencies.id'], name=op.f('fk_questions_competency_id_competencies')),
        sa.ForeignKeyConstraint(['test_id'], ['tests.id'], name=op.f('fk_questions_test_id_tests')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_questions')),
    )
    op.create_table(
        'recommendations',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('competency_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('level', sa.String(length=10), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['competency_id'], ['competencies.id'], name=op.f('fk_recommendations_competency_id_competencies')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_recommendations')),
    )
    op.create_table(
        'answers',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('question_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('score', sa.Numeric(precision=7, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], name=op.f('fk_answers_question_id_questions')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_answers')),
    )
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('phone', sa.String(length=13), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('organization_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('region_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('position', sa.String(length=200), nullable=True),
        sa.Column('experience_years', sa.SmallInteger(), nullable=True),
        sa.Column('education_level', sa.String(length=200), nullable=True),
        sa.Column('qualification_courses', sa.Text(), nullable=True),
        sa.Column('certificates', sa.Text(), nullable=True),
        sa.Column('org_type', sa.String(length=200), nullable=True),
        sa.Column('notifications_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('failed_login_count', sa.SmallInteger(), server_default='0', nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('experience_years >= 0 AND experience_years <= 60', name=op.f('ck_users_experience_years_range')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_users_organization_id_organizations')),
        sa.ForeignKeyConstraint(['region_id'], ['regions.id'], name=op.f('fk_users_region_id_regions')),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_users_role_id_roles')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('phone', name=op.f('uq_users_phone')),
    )
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(length=10), nullable=True),
        sa.Column('is_valid', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_device_tokens_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_device_tokens')),
    )
    op.create_table(
        'expert_reviews',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('expert_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('leader_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('management_culture', sa.SmallInteger(), nullable=False),
        sa.Column('teamwork', sa.SmallInteger(), nullable=False),
        sa.Column('pedagogical_process', sa.SmallInteger(), nullable=False),
        sa.Column('innovation', sa.SmallInteger(), nullable=False),
        sa.Column('documentation', sa.SmallInteger(), nullable=False),
        sa.Column('strategic_planning', sa.SmallInteger(), nullable=False),
        sa.Column('average_score', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('documentation >= 1 AND documentation <= 5', name=op.f('ck_expert_reviews_documentation_range')),
        sa.CheckConstraint('innovation >= 1 AND innovation <= 5', name=op.f('ck_expert_reviews_innovation_range')),
        sa.CheckConstraint('management_culture >= 1 AND management_culture <= 5', name=op.f('ck_expert_reviews_management_culture_range')),
        sa.CheckConstraint('pedagogical_process >= 1 AND pedagogical_process <= 5', name=op.f('ck_expert_reviews_pedagogical_process_range')),
        sa.CheckConstraint('strategic_planning >= 1 AND strategic_planning <= 5', name=op.f('ck_expert_reviews_strategic_planning_range')),
        sa.CheckConstraint('teamwork >= 1 AND teamwork <= 5', name=op.f('ck_expert_reviews_teamwork_range')),
        sa.ForeignKeyConstraint(['expert_id'], ['users.id'], name=op.f('fk_expert_reviews_expert_id_users')),
        sa.ForeignKeyConstraint(['leader_id'], ['users.id'], name=op.f('fk_expert_reviews_leader_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_expert_reviews')),
    )
    op.create_table(
        'feedbacks',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('target_user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("source_type IN ('self', 'staff', 'expert', 'parent', 'superior')", name=op.f('ck_feedbacks_source_type_valid')),
        sa.ForeignKeyConstraint(['source_user_id'], ['users.id'], name=op.f('fk_feedbacks_source_user_id_users')),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], name=op.f('fk_feedbacks_target_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_feedbacks')),
    )
    op.create_table(
        'password_reset_codes',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('code_hash', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.SmallInteger(), server_default='0', nullable=False),
        sa.Column('consumed', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_password_reset_codes_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_password_reset_codes')),
    )
    op.create_table(
        'portfolios',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('file_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], name=op.f('fk_portfolios_file_id_files')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_portfolios_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_portfolios')),
    )
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens')),
    )
    op.create_table(
        'test_sessions',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('test_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('status', sa.String(length=12), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['test_id'], ['tests.id'], name=op.f('fk_test_sessions_test_id_tests')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_test_sessions_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_test_sessions')),
    )
    # Qisman noyob indeks (R7.10): bir foydalanuvchi bitta test uchun bir vaqtda
    # faqat bitta 'in_progress' sessiyaga ega bo'lishi mumkin.
    op.create_index(
        'uq_test_sessions_active_user_test',
        'test_sessions',
        ['user_id', 'test_id'],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
        sqlite_where=sa.text("status = 'in_progress'"),
    )
    op.create_table(
        'session_answers',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('session_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('question_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('selected_answer_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('likert_value', sa.SmallInteger(), nullable=True),
        sa.Column('answered', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], name=op.f('fk_session_answers_question_id_questions')),
        sa.ForeignKeyConstraint(['selected_answer_id'], ['answers.id'], name=op.f('fk_session_answers_selected_answer_id_answers')),
        sa.ForeignKeyConstraint(['session_id'], ['test_sessions.id'], name=op.f('fk_session_answers_session_id_test_sessions')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_session_answers')),
    )
    op.create_table(
        'test_results',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('test_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('session_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('total_score', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('max_score', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('percentage', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('level', sa.String(length=10), nullable=False),
        sa.Column('expert_score', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('next_retake_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('percentage >= 0 AND percentage <= 100', name=op.f('ck_test_results_percentage_range')),
        sa.ForeignKeyConstraint(['session_id'], ['test_sessions.id'], name=op.f('fk_test_results_session_id_test_sessions')),
        sa.ForeignKeyConstraint(['test_id'], ['tests.id'], name=op.f('fk_test_results_test_id_tests')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_test_results_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_test_results')),
        sa.UniqueConstraint('session_id', name=op.f('uq_test_results_session_id')),
    )
    op.create_table(
        'competency_results',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('result_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('competency_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('score', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('max_score', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('percentage', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.CheckConstraint('percentage >= 0 AND percentage <= 100', name=op.f('ck_competency_results_percentage_range')),
        sa.ForeignKeyConstraint(['competency_id'], ['competencies.id'], name=op.f('fk_competency_results_competency_id_competencies')),
        sa.ForeignKeyConstraint(['result_id'], ['test_results.id'], name=op.f('fk_competency_results_result_id_test_results')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_competency_results')),
    )
    op.create_table(
        'result_recommendations',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('result_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('competency_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('level', sa.String(length=10), nullable=True),
        sa.Column('recommendation_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
        sa.Column('text_snapshot', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['competency_id'], ['competencies.id'], name=op.f('fk_result_recommendations_competency_id_competencies')),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], name=op.f('fk_result_recommendations_recommendation_id_recommendations')),
        sa.ForeignKeyConstraint(['result_id'], ['test_results.id'], name=op.f('fk_result_recommendations_result_id_test_results')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_result_recommendations')),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('result_recommendations')
    op.drop_table('competency_results')
    op.drop_table('test_results')
    op.drop_table('session_answers')
    op.drop_index(
        'uq_test_sessions_active_user_test',
        table_name='test_sessions',
        postgresql_where=sa.text("status = 'in_progress'"),
        sqlite_where=sa.text("status = 'in_progress'"),
    )
    op.drop_table('test_sessions')
    op.drop_table('refresh_tokens')
    op.drop_table('portfolios')
    op.drop_table('password_reset_codes')
    op.drop_table('feedbacks')
    op.drop_table('expert_reviews')
    op.drop_table('device_tokens')
    op.drop_table('users')
    op.drop_table('answers')
    op.drop_table('recommendations')
    op.drop_table('questions')
    op.drop_table('organizations')
    op.drop_table('token_blacklist')
    op.drop_table('tests')
    op.drop_table('roles')
    op.drop_table('regions')
    op.drop_table('files')
    op.drop_table('competencies')
