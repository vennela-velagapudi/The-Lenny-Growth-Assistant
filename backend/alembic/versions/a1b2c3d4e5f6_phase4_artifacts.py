"""phase4_artifacts

Revision ID: a1b2c3d4e5f6
Revises: 34e0e3780531
Create Date: 2026-09-15 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '34e0e3780531'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to artifacts table
    op.add_column('artifacts', sa.Column('session_id', sa.Uuid(), nullable=True))
    op.add_column('artifacts', sa.Column('title', sa.String(), nullable=False, server_default='Untitled Artifact'))
    op.add_column('artifacts', sa.Column('metadata_json', sa.String(), nullable=True))
    op.add_column('artifacts', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))
    
    # Make message_id nullable since artifact can belong to session directly
    op.alter_column('artifacts', 'message_id',
               existing_type=sa.Uuid(),
               nullable=True)
               
    # Create foreign key for session_id
    op.create_foreign_key('fk_artifacts_session_id', 'artifacts', 'sessions', ['session_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_artifacts_session_id', 'artifacts', type_='foreignkey')
    op.alter_column('artifacts', 'message_id',
               existing_type=sa.Uuid(),
               nullable=False)
    op.drop_column('artifacts', 'updated_at')
    op.drop_column('artifacts', 'metadata_json')
    op.drop_column('artifacts', 'title')
    op.drop_column('artifacts', 'session_id')
