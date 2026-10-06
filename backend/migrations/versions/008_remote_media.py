"""Track private Appwrite files and durable deletion jobs."""
from alembic import op
revision = '008_remote_media'
down_revision = '007_web_search'
branch_labels = None
depends_on = None

def upgrade():
    from app.models.remote_media import RemoteMedia, RemoteMediaDeletion
    RemoteMedia.__table__.create(op.get_bind(), checkfirst=True)
    RemoteMediaDeletion.__table__.create(op.get_bind(), checkfirst=True)

def downgrade():
    op.drop_table('remote_media')
    op.drop_table('remote_media_deletions')
