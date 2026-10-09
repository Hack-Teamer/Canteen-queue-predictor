"""Initial schema with all tables and indexes

Revision ID: 001_initial
Revises: 
Create Date: 2026-10-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. stations
    op.create_table(
        'stations',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('active_cooks', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 3. menu_items
    op.create_table(
        'menu_items',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('station_id', sa.CHAR(36), sa.ForeignKey('stations.id'), nullable=False),
        sa.Column('prep_minutes', sa.Float(), nullable=False, server_default='2.0'),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 4. orders
    op.create_table(
        'orders',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('token_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('placed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_class_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_orders_status_placed_at', 'orders', ['status', 'placed_at'])

    # 5. order_items
    op.create_table(
        'order_items',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('order_id', sa.CHAR(36), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('menu_item_id', sa.CHAR(36), sa.ForeignKey('menu_items.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('station_id', sa.CHAR(36), sa.ForeignKey('stations.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 6. queue_events
    op.create_table(
        'queue_events',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('order_id', sa.CHAR(36), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_status', sa.String(50), nullable=True),
        sa.Column('to_status', sa.String(50), nullable=False),
        sa.Column('actor_id', sa.CHAR(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_queue_events_order_id', 'queue_events', ['order_id'])

    # 7. predictions
    op.create_table(
        'predictions',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('order_id', sa.CHAR(36), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('pred_low', sa.Float(), nullable=False),
        sa.Column('pred_median', sa.Float(), nullable=False),
        sa.Column('pred_high', sa.Float(), nullable=False),
        sa.Column('actual_wait_minutes', sa.Float(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_predictions_created_at', 'predictions', ['created_at'])

    # 8. crowd_snapshots
    op.create_table(
        'crowd_snapshots',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('people_count', sa.Integer(), nullable=False),
        sa.Column('zone_id', sa.String(100), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_crowd_snapshots_captured_at', 'crowd_snapshots', ['captured_at'])

    # 9. notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_id', sa.CHAR(36), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 10. device_tokens
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(500), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 11. timetable_slots
    op.create_table(
        'timetable_slots',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('bell_time', sa.Time(), nullable=False),
        sa.Column('is_break', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('timetable_slots')
    op.drop_table('device_tokens')
    op.drop_table('notifications')
    op.drop_index('ix_crowd_snapshots_captured_at', table_name='crowd_snapshots')
    op.drop_table('crowd_snapshots')
    op.drop_index('ix_predictions_created_at', table_name='predictions')
    op.drop_table('predictions')
    op.drop_index('ix_queue_events_order_id', table_name='queue_events')
    op.drop_table('queue_events')
    op.drop_table('order_items')
    op.drop_index('ix_orders_status_placed_at', table_name='orders')
    op.drop_table('orders')
    op.drop_table('menu_items')
    op.drop_table('stations')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
