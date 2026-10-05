from alembic import op
from sqlalchemy import inspect,Column,String,ForeignKey
revision='003_activity_owner'
down_revision='002_evidence_clock'
branch_labels=None
depends_on=None
def upgrade():
    columns={c['name'] for c in inspect(op.get_bind()).get_columns('activity')}
    if 'user_id' not in columns:
        with op.batch_alter_table('activity') as batch:
            batch.add_column(Column('user_id',String(64),nullable=True))
            batch.create_foreign_key('fk_activity_user','users',['user_id'],['id'])
            batch.create_index('ix_activity_user_id',['user_id'])
def downgrade():raise RuntimeError('Restore a backup to preserve audit history.')
