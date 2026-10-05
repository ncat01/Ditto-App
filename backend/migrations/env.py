from alembic import context
from sqlalchemy import create_engine
from app.config import get_settings
from app.database.db import Base
from app.models import tables
config=context.config
target_metadata=Base.metadata
engine=create_engine(get_settings().database_url)
with engine.connect() as connection:
    context.configure(connection=connection,target_metadata=target_metadata,render_as_batch=True)
    with context.begin_transaction():context.run_migrations()
