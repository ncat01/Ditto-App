from alembic import op
from app.database.db import Base
from app.models import ledger
revision='004_normalized_records'
down_revision='003_activity_owner'
branch_labels=None
depends_on=None
def upgrade():Base.metadata.create_all(op.get_bind())
def downgrade():raise RuntimeError('Restore a backup to preserve evidence.')
