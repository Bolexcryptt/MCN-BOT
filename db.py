import aiosqlite

DB_NAME = "data/bot.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            points INTEGER DEFAULT 0,
            last_checkin TEXT,
            daily_defend_count INTEGER DEFAULT 0,
            invites INTEGER DEFAULT 0,
            total_vaults INTEGER DEFAULT 0
        )
        """)

        columns_cursor = await db.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in await columns_cursor.fetchall()]

        for column_name, column_sql in {
            "username": "ALTER TABLE users ADD COLUMN username TEXT",
            "first_name": "ALTER TABLE users ADD COLUMN first_name TEXT",
            "points": "ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0",
            "last_checkin": "ALTER TABLE users ADD COLUMN last_checkin TEXT",
            "daily_defend_count": "ALTER TABLE users ADD COLUMN daily_defend_count INTEGER DEFAULT 0",
            "invites": "ALTER TABLE users ADD COLUMN invites INTEGER DEFAULT 0",
            "total_vaults": "ALTER TABLE users ADD COLUMN total_vaults INTEGER DEFAULT 0",
        }.items():
            if column_name not in columns:
                await db.execute(column_sql)

        await db.commit()


async def ensure_user(user):
    username = user.username or user.first_name or "Guardian"
    first_name = user.first_name or username
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        INSERT INTO users (user_id, username, first_name, points, last_checkin, daily_defend_count, invites, total_vaults)
        VALUES (?, ?, ?, 0, NULL, 0, 0, 0)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
        """, (user.id, username, first_name))
        await db.commit()


async def add_points(user, points):
    await ensure_user(user)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE users
        SET points = points + ?
        WHERE user_id = ?
        """, (points, user.id))
        await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id, username, points, last_checkin, daily_defend_count, invites, total_vaults, first_name FROM users WHERE user_id = ?",
            (user_id,)
        )
        return await cursor.fetchone()


async def update_defend_count(user_id, count):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET daily_defend_count = ? WHERE user_id = ?",
            (count, user_id)
        )
        await db.commit()


async def add_invite(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE users
        SET invites = invites + 1
        WHERE user_id = ?
        """, (user_id,))
        await db.commit()


async def add_vault_completion(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET total_vaults = total_vaults + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def get_leaderboard(limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT username, points, total_vaults FROM users ORDER BY points DESC, total_vaults DESC LIMIT ?",
            (limit,)
        )
        return await cursor.fetchall()