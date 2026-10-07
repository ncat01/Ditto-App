from alembic import context
from sqlalchemy import create_engine
from app.config import get_settings
from app.database.db import Base, engine
from app.models import tables, ledger, integrations, account_security, remote_media, refresh_tokens, jobs
config=context.config
target_metadata=Base.metadata
with engine.connect() as connection:
    context.configure(connection=connection,target_metadata=target_metadata,render_as_batch=True)
    with context.begin_transaction():context.run_migrations()
