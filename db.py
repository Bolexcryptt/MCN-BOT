import aiosqlite

DB_NAME = "data/bot.db"

RANKS = (
    ("Initiate", 0),
    ("Guardian 🐾", 100),
    ("Elite Guardian", 500),
    ("Royal Guardian", 1500),
    ("Ambassador 👑", 5000),
)

USER_COLUMNS = {
    "username": "TEXT",
    "first_name": "TEXT",
    "points": "INTEGER DEFAULT 0",
    "last_checkin": "TEXT",
    "daily_defend_count": "INTEGER DEFAULT 0",
    "invites": "INTEGER DEFAULT 0",
    "invite_energy": "INTEGER DEFAULT 0",
    "total_vaults": "INTEGER DEFAULT 0",
    "rank": "TEXT DEFAULT 'Initiate'",
    "daily_streak": "INTEGER DEFAULT 0",
    "last_vault_date": "TEXT",
    "vault_progress": "INTEGER DEFAULT 0",
    "vault_question": "TEXT",
    "vault_answer": "TEXT",
    "last_challenge_date": "TEXT",
    "daily_challenge_date": "TEXT",
    "daily_challenge_question": "TEXT",
    "daily_challenge_answer": "TEXT",
}


def rank_for_energy(energy: int) -> tuple[str, int | None, int, int]:
    for index in range(len(RANKS) - 1, -1, -1):
        name, threshold = RANKS[index]
        if energy >= threshold:
            next_threshold = RANKS[index + 1][1] if index + 1 < len(RANKS) else None
            previous_threshold = threshold
            return name, next_threshold, previous_threshold, index
    return RANKS[0][0], RANKS[1][1], 0, 0


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
        columns = {row[1] for row in await columns_cursor.fetchall()}
        for column_name, column_sql in USER_COLUMNS.items():
            if column_name not in columns:
                await db.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_sql}")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            invited_id INTEGER PRIMARY KEY,
            inviter_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        cursor = await db.execute("SELECT user_id, points FROM users")
        for user_id, energy in await cursor.fetchall():
            await _update_rank(db, user_id, energy or 0)
        await db.commit()


async def ensure_user(user):
    username = user.username
    first_name = user.first_name or username or "Guardian"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        INSERT INTO users (user_id, username, first_name, points, last_checkin, daily_defend_count, invites, total_vaults, rank)
        VALUES (?, ?, ?, 0, NULL, 0, 0, 0, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
        """, (user.id, username, first_name, RANKS[0][0]))
        cursor = await db.execute("SELECT points FROM users WHERE user_id = ?", (user.id,))
        await _update_rank(db, user.id, (await cursor.fetchone())[0])
        await db.commit()


async def _update_rank(db, user_id: int, energy: int) -> str:
    rank = rank_for_energy(energy)[0]
    await db.execute("UPDATE users SET rank = ? WHERE user_id = ?", (rank, user_id))
    return rank


async def add_points(user, points):
    await ensure_user(user)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user.id))
        cursor = await db.execute("SELECT points FROM users WHERE user_id = ?", (user.id,))
        await _update_rank(db, user.id, (await cursor.fetchone())[0])
        await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """SELECT user_id, username, points, last_checkin, daily_defend_count,
                      invites, total_vaults, first_name, rank, daily_streak,
                      last_vault_date, vault_progress, vault_question, vault_answer,
                      last_challenge_date, daily_challenge_date,
                      daily_challenge_question, daily_challenge_answer
               FROM users WHERE user_id = ?""",
            (user_id,),
        )
        return await cursor.fetchone()


async def update_defend_count(user_id, count):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET daily_defend_count = ? WHERE user_id = ?",
            (count, user_id),
        )
        await db.commit()


async def add_invite(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET invites = invites + 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def record_referral(invited_id: int, inviter_id: int, created_at: str) -> bool:
    if invited_id == inviter_id:
        return False

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT 1 FROM referrals WHERE invited_id = ?",
            (invited_id,),
        )
        if await cursor.fetchone():
            await db.commit()
            return False

        await db.execute(
            """INSERT INTO users (user_id, username, first_name, points, invites, total_vaults, rank)
               VALUES (?, 'Guardian', 'Guardian', 0, 0, 0, ?) ON CONFLICT(user_id) DO NOTHING""",
            (inviter_id, RANKS[0][0]),
        )
        await db.execute(
            "INSERT INTO referrals (invited_id, inviter_id, created_at) VALUES (?, ?, ?)",
            (invited_id, inviter_id, created_at),
        )
        await db.execute(
            """UPDATE users SET invites = invites + 1, invite_energy = invite_energy + 50,
                      points = points + 50 WHERE user_id = ?""",
            (inviter_id,),
        )
        cursor = await db.execute("SELECT points FROM users WHERE user_id = ?", (inviter_id,))
        await _update_rank(db, inviter_id, (await cursor.fetchone())[0])
        await db.commit()
        return True


async def get_invite_stats(user_id: int) -> tuple[int, int]:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT invites, invite_energy FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return (row[0], row[1]) if row else (0, 0)


async def add_vault_completion(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET total_vaults = total_vaults + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def save_vault_state(
    user_id: int,
    vault_date: str,
    progress: int,
    question: str | None,
    answer: str | None,
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """UPDATE users SET last_vault_date = ?, vault_progress = ?,
                      vault_question = ?, vault_answer = ? WHERE user_id = ?""",
            (vault_date, progress, question, answer, user_id),
        )
        await db.commit()


async def award_vault_answer(user_id: int, expected_progress: int, today: str) -> tuple[bool, int]:
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            """UPDATE users SET points = points + 5, vault_progress = vault_progress + 1,
                      total_vaults = total_vaults + CASE WHEN vault_progress + 1 = ? THEN 1 ELSE 0 END,
                      vault_question = NULL, vault_answer = NULL
               WHERE user_id = ? AND last_vault_date = ? AND vault_progress = ?""",
            (5, user_id, today, expected_progress),
        )
        if cursor.rowcount != 1:
            await db.rollback()
            return False, 0
        cursor = await db.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        energy = (await cursor.fetchone())[0]
        await _update_rank(db, user_id, energy)
        await db.commit()
        return True, energy


async def claim_daily(user_id: int, today: str) -> tuple[bool, int, int]:
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT points, last_checkin, daily_streak FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            await db.rollback()
            raise ValueError(f"Guardian {user_id} must be registered before claiming daily energy")

        energy, last_claim, streak = row
        if last_claim == today:
            await db.commit()
            return False, streak, energy

        from datetime import date, timedelta

        yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
        streak = streak + 1 if last_claim == yesterday else 1
        reward = 5 + (25 if streak % 7 == 0 else 0)
        energy += reward
        await db.execute(
            "UPDATE users SET points = ?, last_checkin = ?, daily_streak = ? WHERE user_id = ?",
            (energy, today, streak, user_id),
        )
        await _update_rank(db, user_id, energy)
        await db.commit()
        return True, streak, energy


async def start_daily_challenge(
    user_id: int,
    today: str,
    question: str,
    answer: str,
) -> tuple[str, str | None, str | None]:
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            """SELECT last_challenge_date, daily_challenge_date,
                      daily_challenge_question, daily_challenge_answer
               FROM users WHERE user_id = ?""",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            await db.rollback()
            raise ValueError(f"Guardian {user_id} must be registered before starting a daily challenge")
        completed_date, challenge_date, saved_question, saved_answer = row
        if completed_date == today:
            await db.commit()
            return "completed", None, None
        if challenge_date == today and saved_answer:
            await db.commit()
            return "pending", saved_question, saved_answer

        await db.execute(
            """UPDATE users SET daily_challenge_date = ?, daily_challenge_question = ?,
                      daily_challenge_answer = ? WHERE user_id = ?""",
            (today, question, answer, user_id),
        )
        await db.commit()
        return "started", question, answer


async def complete_daily_challenge(user_id: int, today: str, answer: str) -> tuple[bool, int]:
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            """SELECT points FROM users WHERE user_id = ? AND daily_challenge_date = ?
                      AND daily_challenge_answer = ?
                      AND (last_challenge_date IS NULL OR last_challenge_date != ?)""",
            (user_id, today, answer, today),
        )
        row = await cursor.fetchone()
        if row is None:
            await db.rollback()
            return False, 0
        energy = row[0] + 10
        await db.execute(
            """UPDATE users SET points = ?, last_challenge_date = ?,
                      daily_challenge_answer = NULL, daily_challenge_question = NULL
               WHERE user_id = ?""",
            (energy, today, user_id),
        )
        await _update_rank(db, user_id, energy)
        await db.commit()
        return True, energy


async def get_leaderboard(limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """SELECT username, points, total_vaults, first_name FROM users
               ORDER BY points DESC, total_vaults DESC LIMIT ?""",
            (limit,),
        )
        return await cursor.fetchall()
