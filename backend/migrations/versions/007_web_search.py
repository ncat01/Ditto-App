from alembic import op
from app.models.account_security import WebSearchRecord
revision='007_web_search'
down_revision='006_account_security'
branch_labels=None
depends_on=None

def upgrade():WebSearchRecord.__table__.create(op.get_bind(),checkfirst=True)
def downgrade():WebSearchRecord.__table__.drop(op.get_bind(),checkfirst=True)
