from alembic import op
import sqlalchemy as sa

# ревизии
revision = "183714bcb3ee"
down_revision = "746c5bf7e39e"

branch_labels = None
depends_on = None


def upgrade():
    # 0) если есть данные и они не важны — подчистим (иначе новый FK не применится)
    op.execute("TRUNCATE TABLE event_players CASCADE;")
    op.execute("TRUNCATE TABLE events CASCADE;")

    # 1) Заменяем FK у events.creator_id: с users.id -> на users.telegram_id
    # ВАЖНО: имя текущего FK может отличаться!
    # Посмотри в psql: \d events  (ищи строку "Foreign-key constraints: ... creator_id ...")
    old_fk_name = "events_creator_id_fkey"   # <- при необходимости поменяй
    op.drop_constraint(old_fk_name, "events", type_="foreignkey")

    op.create_foreign_key(
        "events_creator_tg_fkey",
        source_table="events",
        referent_table="users",
        local_cols=["creator_id"],
        remote_cols=["telegram_id"],
        ondelete="RESTRICT",
    )

    # 2) Пересоздаём event_players под telegram_id
    # если таблица есть — дропнем
    op.drop_table("event_players")

    op.create_table(
        "event_players",
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_telegram_id", sa.Integer(), sa.ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade():
    # Откатываем обратно на users.id

    # 1) event_players: вернуть user_id
    op.drop_table("event_players")
    op.create_table(
        "event_players",
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    )

    # 2) FK у events.creator_id вернуть на users.id
    op.drop_constraint("events_creator_tg_fkey", "events", type_="foreignkey")
    op.create_foreign_key(
        "events_creator_id_fkey",
        source_table="events",
        referent_table="users",
        local_cols=["creator_id"],
        remote_cols=["id"],
        ondelete="RESTRICT",
    )
