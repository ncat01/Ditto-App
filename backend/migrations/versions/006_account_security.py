from alembic import op
from app.models.account_security import AccountToken, AccountVerification, RequestBudget, MediaDeletion
revision = '006_account_security'
down_revision = '005_instagram_oauth'
branch_labels = None
depends_on = None

def upgrade():
    for model in [AccountToken, AccountVerification, RequestBudget, MediaDeletion]:
        model.__table__.create(op.get_bind(), checkfirst=True)

def downgrade():
    for model in [MediaDeletion, RequestBudget, AccountVerification, AccountToken]:
        model.__table__.drop(op.get_bind(), checkfirst=True)
