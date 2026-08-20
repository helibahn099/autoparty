"""Idempotent column/table upgrades for existing demo volumes."""

from sqlalchemy import text

from app.database import engine


STATEMENTS = [
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS address VARCHAR(255)",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS lng DOUBLE PRECISION",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS whatsapp VARCHAR(40)",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS telegram VARCHAR(80)",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS instagram VARCHAR(80)",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS pickup_note VARCHAR(255)",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS strike_count INTEGER DEFAULT 0",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS new_orders_blocked_until TIMESTAMPTZ",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS completed_orders_count INTEGER DEFAULT 0",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS confirmed_reports_count INTEGER DEFAULT 0",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS false_availability_count INTEGER DEFAULT 0",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS is_partner BOOLEAN DEFAULT FALSE",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS partner_level INTEGER",
    "ALTER TABLE seller_profiles ADD COLUMN IF NOT EXISTS display_rating DOUBLE PRECISION DEFAULT 4.2",
    "ALTER TABLE cities ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION",
    "ALTER TABLE cities ADD COLUMN IF NOT EXISTS lng DOUBLE PRECISION",
    "ALTER TABLE cities ADD COLUMN IF NOT EXISTS name_en VARCHAR(120)",
    "ALTER TABLE cities ADD COLUMN IF NOT EXISTS name_ky VARCHAR(120)",
    "ALTER TABLE cities ADD COLUMN IF NOT EXISTS search_radius_km DOUBLE PRECISION DEFAULT 8",
    "ALTER TABLE regions ADD COLUMN IF NOT EXISTS name_en VARCHAR(120)",
    "ALTER TABLE regions ADD COLUMN IF NOT EXISTS name_ky VARCHAR(120)",
    "ALTER TABLE countries ADD COLUMN IF NOT EXISTS name_en VARCHAR(120)",
    "ALTER TABLE countries ADD COLUMN IF NOT EXISTS name_ky VARCHAR(120)",
    "ALTER TABLE categories ADD COLUMN IF NOT EXISTS name_en VARCHAR(120)",
    "ALTER TABLE categories ADD COLUMN IF NOT EXISTS name_ky VARCHAR(120)",
    "ALTER TABLE popular_parts ADD COLUMN IF NOT EXISTS name_en VARCHAR(160)",
    "ALTER TABLE popular_parts ADD COLUMN IF NOT EXISTS name_ky VARCHAR(160)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS batch_id VARCHAR(40)",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS batch_id VARCHAR(40)",
    "ALTER TABLE seller_offer_items ADD COLUMN IF NOT EXISTS detail TEXT",
    "ALTER TABLE seller_offer_items ADD COLUMN IF NOT EXISTS condition VARCHAR(20)",
    "ALTER TABLE seller_offer_items ADD COLUMN IF NOT EXISTS is_original BOOLEAN",
    """
    CREATE TABLE IF NOT EXISTS user_vehicles (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        brand_id INTEGER REFERENCES vehicle_brands(id),
        model_id INTEGER REFERENCES vehicle_models(id),
        year INTEGER,
        nickname VARCHAR(80),
        is_default BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_user_vehicles_user_id ON user_vehicles (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_orders_batch_id ON orders (batch_id)",
    """
    CREATE TABLE IF NOT EXISTS reports (
        id SERIAL PRIMARY KEY,
        reporter_id INTEGER NOT NULL REFERENCES users(id),
        seller_id INTEGER NOT NULL REFERENCES seller_profiles(id),
        order_id INTEGER REFERENCES orders(id),
        chat_id INTEGER REFERENCES chats(id),
        reason VARCHAR(40) NOT NULL,
        comment VARCHAR(1000),
        status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        reviewed_at TIMESTAMPTZ,
        reviewed_by_id INTEGER REFERENCES users(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_reports_seller_id ON reports (seller_id)",
    "CREATE INDEX IF NOT EXISTS ix_reports_status ON reports (status)",
    """
    CREATE TABLE IF NOT EXISTS platform_settings (
        id INTEGER PRIMARY KEY,
        rotation_after_orders INTEGER DEFAULT 20,
        rotation_lookback_hours INTEGER DEFAULT 24,
        rotation_max_extra_delay INTEGER DEFAULT 40,
        strike_limit INTEGER DEFAULT 3,
        strike_ban_days INTEGER DEFAULT 30
    )
    """,
    """
    INSERT INTO platform_settings (id, rotation_after_orders, rotation_lookback_hours, rotation_max_extra_delay, strike_limit, strike_ban_days)
    VALUES (1, 20, 24, 40, 3, 30)
    ON CONFLICT (id) DO NOTHING
    """,
]


ENUM_VALUES = [
    ("availability", "PARTIAL"),
    ("notificationtype", "REPORT"),
]


def _add_enum_value(conn, type_name: str, label: str) -> None:
    exists = conn.execute(
        text(
            """
            SELECT 1
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = :type_name AND e.enumlabel = :label
            """
        ),
        {"type_name": type_name, "label": label},
    ).first()
    if exists:
        return
    conn.execute(text(f"ALTER TYPE {type_name} ADD VALUE '{label}'"))


def ensure_schema() -> None:
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            conn.execute(text(stmt))
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for type_name, label in ENUM_VALUES:
            try:
                _add_enum_value(conn, type_name, label)
            except Exception:
                pass
