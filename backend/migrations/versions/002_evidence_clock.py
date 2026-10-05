"""Separate permission/attribution signals and durable demo clock."""
from alembic import op
from sqlalchemy import inspect,Column,Boolean,Text
from app.database.db import Base
from app.models import tables
revision='002_evidence_clock'
down_revision='001_durable_accounts'
branch_labels=None
depends_on=None
def upgrade():
    bind=op.get_bind()
    columns={c['name'] for c in inspect(bind).get_columns('candidate_matches')}
    with op.batch_alter_table('candidate_matches') as batch:
        for name in ['attribution_present','permission_granted']:
            if name not in columns:batch.add_column(Column(name,Boolean,nullable=False,server_default='0'))
    if bind.dialect.name=='postgresql':op.alter_column('content','perceptual_hash',type_=Text())
    Base.metadata.create_all(bind)
def downgrade():raise RuntimeError('Restore a database backup rather than discard audit evidence.')
