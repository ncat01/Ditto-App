"""Per-user Instagram OAuth tables."""
from alembic import op
import sqlalchemy as sa
revision='005_instagram_oauth'
down_revision='004_normalized_records'
branch_labels=None
depends_on=None

def upgrade():
    if 'instagram_connections' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table('instagram_connections',sa.Column('user_id',sa.String(64),sa.ForeignKey('users.id'),primary_key=True),sa.Column('instagram_user_id',sa.String(64),unique=True,nullable=False),sa.Column('username',sa.String(128),nullable=False),sa.Column('encrypted_token',sa.Text,nullable=False),sa.Column('expires_at',sa.DateTime,nullable=False),sa.Column('refreshed_at',sa.DateTime,nullable=False))
    if 'instagram_oauth_attempts' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table('instagram_oauth_attempts',sa.Column('state_hash',sa.String(64),primary_key=True),sa.Column('user_id',sa.String(64),sa.ForeignKey('users.id'),nullable=False),sa.Column('session_hash',sa.String(64),nullable=False),sa.Column('cookie_hash',sa.String(64),nullable=True),sa.Column('expires_at',sa.DateTime,nullable=False))
    if 'ix_instagram_oauth_attempts_user_id' not in [i['name'] for i in sa.inspect(op.get_bind()).get_indexes('instagram_oauth_attempts')]:
        op.create_index('ix_instagram_oauth_attempts_user_id','instagram_oauth_attempts',['user_id'])

def downgrade():
    op.drop_table('instagram_oauth_attempts');op.drop_table('instagram_connections')
