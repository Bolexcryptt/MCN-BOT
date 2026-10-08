import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import aiosqlite
import db
from handlers.navigation import _make_artwork
from PIL import Image


class GuardianProgressionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temp_dir.name) / "guardians.db")
        self.database_patch = patch.object(db, "DB_NAME", self.database_path)
        self.database_patch.start()
        await db.init_db()

    async def asyncTearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    async def test_vault_energy_and_completion_persist_in_database(self):
        guardian = SimpleNamespace(id=101, username="sentinel", first_name="Sentinel")
        await db.ensure_user(guardian)
        await db.save_vault_state(101, "2026-10-02", 0, "What protects the Vault?", "the vault")

        for progress in range(5):
            accepted, energy = await db.award_vault_answer(101, progress, "2026-10-02")
            self.assertTrue(accepted)
            self.assertEqual(energy, (progress + 1) * 5)

        data = await db.get_user(101)
        self.assertEqual(data[2], 25)
        self.assertEqual(data[6], 1)
        self.assertEqual(data[8], "🐾 Guardian")
        self.assertFalse((await db.award_vault_answer(101, 4, "2026-10-02"))[0])

    async def test_referral_is_durable_and_awarded_only_once(self):
        await db.ensure_user(SimpleNamespace(id=202, username="recruiter", first_name="Recruiter"))

        self.assertTrue(await db.record_referral(303, 202, "2026-10-02"))
        self.assertFalse(await db.record_referral(303, 202, "2026-10-02"))

        data = await db.get_user(202)
        self.assertEqual(data[2], 50)
        self.assertEqual(data[5], 1)
        self.assertEqual(await db.get_invite_stats(202), (1, 50))

    async def test_daily_claim_and_seventh_day_streak_are_idempotent(self):
        await db.ensure_user(SimpleNamespace(id=404, username=None, first_name="Guardian"))

        for day in range(1, 8):
            date = f"2026-10-{day:02d}"
            claimed, streak, _ = await db.claim_daily(404, date)
            self.assertTrue(claimed)
            self.assertEqual(streak, day)

        claimed, streak, energy = await db.claim_daily(404, "2026-10-07")
        self.assertFalse(claimed)
        self.assertEqual(streak, 7)
        self.assertEqual(energy, 60)

        data = await db.get_user(404)
        self.assertEqual(data[9], 7)
        self.assertEqual(data[1], None)
        self.assertEqual(data[7], "Guardian")

    async def test_daily_challenge_can_be_completed_once(self):
        await db.ensure_user(SimpleNamespace(id=505, username="oria_guardian", first_name="Guardian"))
        status, question, answer = await db.start_daily_challenge(
            505, "2026-10-02", "Who watches the system?", "oria"
        )
        self.assertEqual((status, question, answer), ("started", "Who watches the system?", "oria"))
        self.assertEqual(
            await db.start_daily_challenge(505, "2026-10-02", "Unused?", "unused"),
            ("pending", "Who watches the system?", "oria"),
        )
        self.assertEqual(await db.complete_daily_challenge(505, "2026-10-02", "oria"), (True, 10))
        self.assertEqual(await db.complete_daily_challenge(505, "2026-10-02", "oria"), (False, 0))

    async def test_rank_updates_and_generated_art_is_telegram_ready_png(self):
        guardian = SimpleNamespace(id=606, username="guardian", first_name="Guardian")
        await db.ensure_user(guardian)
        await db.add_points(guardian, 500)
        self.assertEqual((await db.get_user(606))[8], "⭐️ Elite Guardian")

        image = Image.open(BytesIO(_make_artwork("Vault Trial")))
        self.assertEqual(image.format, "PNG")
        self.assertEqual(image.size, (900, 360))

    async def test_existing_guardian_records_survive_schema_migration(self):
        legacy_path = str(Path(self.temp_dir.name) / "legacy.db")
        with patch.object(db, "DB_NAME", legacy_path):
            async with aiosqlite.connect(legacy_path) as connection:
                await connection.execute("""
                    CREATE TABLE users (
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
                await connection.execute(
                    """INSERT INTO users
                       (user_id, username, first_name, points, invites, total_vaults)
                       VALUES (707, 'legacy_guardian', 'Legacy', 800, 3, 4)"""
                )
                await connection.commit()

            await db.init_db()
            migrated = await db.get_user(707)

        self.assertEqual(migrated[2], 800)
        self.assertEqual(migrated[5], 3)
        self.assertEqual(migrated[6], 4)
        self.assertEqual(migrated[8], "⭐️ Elite Guardian")


if __name__ == "__main__":
    unittest.main()
