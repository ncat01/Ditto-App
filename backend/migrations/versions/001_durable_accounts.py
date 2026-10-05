"""Baseline and additive migration for the supplied single-user database."""
from alembic import op
from sqlalchemy import inspect, Column, String
from app.database.db import Base
from app.models import tables
revision='001_durable_accounts'
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    bind=op.get_bind()
    existing=inspect(bind).get_table_names()
    if 'users' in existing:
        columns={c['name'] for c in inspect(bind).get_columns('users')}
        with op.batch_alter_table('users') as batch:
            for name,size in [('email',254),('salt',64),('password_hash',64)]:
                if name not in columns:batch.add_column(Column(name,String(size),nullable=True))
            batch.create_index('ix_users_email','email'.split(),unique=True)
    Base.metadata.create_all(bind)
def downgrade():
    raise RuntimeError('Destructive downgrade is intentionally unsupported; restore a database backup.')
