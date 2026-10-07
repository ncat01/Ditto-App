"""Durable measured-comparison queue and private candidate media."""
revision = '010_processing_jobs'
down_revision = '009_rotating_auth'
branch_labels = None
depends_on = None

def upgrade():
    from alembic import op
    from app.models.jobs import ProcessingJob, CandidateMedia
    ProcessingJob.__table__.create(op.get_bind(), checkfirst=True)
    CandidateMedia.__table__.create(op.get_bind(), checkfirst=True)

def downgrade():
    raise RuntimeError('Destructive downgrade is disabled; preserve processing and media records.')
