"""Initial schema - create all base tables

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table first (other tables depend on it)
    op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('auth_provider', sa.String(), nullable=True),
        sa.Column('google_access_token', sa.String(), nullable=True),
        sa.Column('google_refresh_token', sa.String(), nullable=True),
        sa.Column('microsoft_access_token', sa.String(), nullable=True),
        sa.Column('microsoft_refresh_token', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create reminders table
    op.create_table('reminders',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('text', sa.String(), nullable=False),
        sa.Column('due_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'CANCELLED', name='reminderstatus'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create interactions table
    op.create_table('interactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('user_message', sa.String(), nullable=False),
        sa.Column('assistant_response', sa.String(), nullable=False),
        sa.Column('intent', sa.String(), nullable=True),
        sa.Column('entities', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create messaging_accounts table
    op.create_table('messaging_accounts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('account_id', sa.String(), nullable=False),
        sa.Column('account_name', sa.String(), nullable=True),
        sa.Column('channel_id', sa.String(), nullable=True),
        sa.Column('bot_token', sa.String(), nullable=True),
        sa.Column('webhook_url', sa.String(), nullable=True),
        sa.Column('access_token', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_webhook_active', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messaging_accounts_platform'), 'messaging_accounts', ['platform'], unique=False)

    # Create user_memory table
    op.create_table('user_memory',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_memory_user_id'), 'user_memory', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_memory_user_id'), table_name='user_memory')
    op.drop_table('user_memory')
    op.drop_index(op.f('ix_messaging_accounts_platform'), table_name='messaging_accounts')
    op.drop_table('messaging_accounts')
    op.drop_table('interactions')
    op.drop_table('reminders')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    # Drop enum type
    sa.Enum(name='reminderstatus').drop(op.get_bind(), checkfirst=True)
