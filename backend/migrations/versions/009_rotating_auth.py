"""Preserve existing hashes; widen for Argon2 and add rotating refresh families."""
from alembic import op
from sqlalchemy import inspect, String, Column
revision = '009_rotating_auth'
down_revision = '008_remote_media'
branch_labels = None
depends_on = None


def upgrade():
    from app.models.refresh_tokens import RefreshFamily, RefreshToken
    bind = op.get_bind()
    with op.batch_alter_table('users') as batch:
        batch.alter_column('password_hash', existing_type=String(64), type_=String(255))
    if 'family_id' not in {c['name'] for c in inspect(bind).get_columns('auth_sessions')}:
        with op.batch_alter_table('auth_sessions') as batch:
            batch.add_column(Column('family_id', String(32), nullable=True))
            batch.create_index('ix_auth_sessions_family_id', ['family_id'])
    RefreshFamily.__table__.create(bind, checkfirst=True)
    RefreshToken.__table__.create(bind, checkfirst=True)


def downgrade():
    raise RuntimeError('Restore a reviewed backup rather than destroy authentication records.')
