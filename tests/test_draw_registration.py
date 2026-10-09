import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import db
from handlers import draw
from handlers.navigation import _resolve_asset_path
from handlers.profile import RANK_ARTWORK, show_profile


class DrawRegistrationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_patch = patch.object(
            db, "DB_NAME", str(Path(self.temp_dir.name) / "draw.db")
        )
        self.database_patch.start()
        await db.init_db()

    async def asyncTearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    async def test_wallet_is_registered_only_once_case_insensitively(self):
        registered = await db.register_draw_wallet(
            100, "0x1234567890abcdef1234567890abcdef12345678", "20", 12.0, 0.6
        )
        duplicate = await db.register_draw_wallet(
            200, "0x1234567890ABCDEF1234567890ABCDEF12345678", "20", 12.0, 0.6
        )

        self.assertTrue(registered)
        self.assertFalse(duplicate)
        entries = await db.get_draw_registrations()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][0], 100)

    async def test_final_recheck_persists_pass_fail_and_error_states(self):
        wallet = "0x1234567890abcdef1234567890abcdef12345678"
        await db.register_draw_wallet(100, wallet, "20", 12.0, 0.6)

        await db.update_draw_final_check(wallet, False, "failed", "now", "10", 6.0)
        row = (await db.get_draw_registrations())[0]
        self.assertEqual(row[7], 0)
        self.assertEqual(row[9], "10")
        self.assertEqual(row[10], 6.0)
        self.assertEqual(row[11], "failed")

        await db.update_draw_final_check(wallet, None, "error", "later", None, None)
        row = (await db.get_draw_registrations())[0]
        self.assertIsNone(row[7])
        self.assertEqual(row[11], "error")


class DrawAccessAndRankVisualTest(unittest.TestCase):
    def test_draw_admin_requires_configured_numeric_owner_and_private_chat(self):
        user = SimpleNamespace(id=123)
        private_chat = SimpleNamespace(type="private")
        group_chat = SimpleNamespace(type="supergroup")
        with patch.object(draw, "MCN_OWNER_ID", 123):
            self.assertTrue(draw._is_owner(user, private_chat))
            self.assertFalse(draw._is_owner(user, group_chat))
            self.assertFalse(draw._is_owner(SimpleNamespace(id=124), private_chat))
        with patch.object(draw, "MCN_OWNER_ID", None):
            self.assertFalse(draw._is_owner(user, private_chat))

    def test_wallet_validation_rejects_invalid_address_shapes(self):
        self.assertTrue(draw._wallet_is_valid("0x1234567890abcdef1234567890abcdef12345678"))
        self.assertFalse(draw._wallet_is_valid("0x123"))
        self.assertFalse(draw._wallet_is_valid("0x" + "g" * 40))

    def test_every_rank_profile_selects_an_existing_role_aligned_artwork(self):
        self.assertEqual(len(RANK_ARTWORK), len(db.RANKS))
        expected_files = (
            "guardians.png",
            "royalguardians.png",
            "eliteguardians.png",
            "ambassador.png",
            "vaultguardian.png",
            "legend.png",
        )
        for label, filename in zip(RANK_ARTWORK, expected_files):
            with self.subTest(rank=label):
                self.assertTrue(_resolve_asset_path(label).endswith(filename))

    def test_csv_export_contains_required_participant_fields(self):
        csv_bytes = draw._make_participants_csv(
            [
                (
                    100,
                    "0x1234567890abcdef1234567890abcdef12345678",
                    "2026-10-09 12:00:00 UTC",
                    "20",
                    12.0,
                    0.6,
                    1,
                    1,
                    "2026-10-09 13:00:00 UTC",
                    "20",
                    12.0,
                    "passed",
                )
            ]
        )
        csv_text = csv_bytes.decode("utf-8-sig")
        self.assertIn("wallet_address", csv_text)
        self.assertIn("registration_mcn_balance", csv_text)
        self.assertIn("registration_usd_value", csv_text)
        self.assertIn("registration_eligibility", csv_text)
        self.assertIn("registered_at_utc", csv_text)
        self.assertIn("final_check_status", csv_text)
        self.assertIn("2026-10-09 12:00:00 UTC", csv_text)

    def test_new_registration_is_not_misreported_as_already_final_checked(self):
        row = (
            100,
            "0x1234567890abcdef1234567890abcdef12345678",
            "2026-10-09 12:00:00 UTC",
            "20",
            12.0,
            0.6,
            1,
            0,
            None,
            None,
            None,
            None,
        )
        self.assertIn("Not checked", draw._registration_row(row))


class DrawMessageFlowTest(unittest.IsolatedAsyncioTestCase):
    def make_message(self, wallet, user_id=123):
        return SimpleNamespace(
            text=wallet,
            from_user=SimpleNamespace(id=user_id, username="guardian", first_name="Guardian"),
            chat=SimpleNamespace(type="private"),
            answer=AsyncMock(),
        )

    async def test_eligible_wallet_is_registered_after_live_checks(self):
        wallet = "0x1234567890abcdef1234567890abcdef12345678"
        message = self.make_message(wallet)
        state = SimpleNamespace(get_data=AsyncMock(return_value={}), clear=AsyncMock())
        with (
            patch(
                "handlers.draw.fetch_mcn_price_usd",
                new_callable=AsyncMock,
                return_value=(Decimal("1"), "2026-10-09 12:00:00 UTC"),
            ),
            patch(
                "handlers.draw.fetch_wallet_mcn_balance",
                new_callable=AsyncMock,
                return_value=Decimal("10"),
            ),
            patch(
                "handlers.draw.register_draw_wallet",
                new_callable=AsyncMock,
                return_value=True,
            ) as register,
        ):
            await draw.receive_wallet_for_draw(message, state)

        register.assert_awaited_once()
        self.assertIn("✅ Eligible", message.answer.await_args_list[0].args[0])
        state.clear.assert_awaited_once()

    async def test_insufficient_balance_is_not_registered(self):
        wallet = "0x1234567890abcdef1234567890abcdef12345678"
        message = self.make_message(wallet)
        state = SimpleNamespace(get_data=AsyncMock(return_value={}), clear=AsyncMock())
        with (
            patch(
                "handlers.draw.fetch_mcn_price_usd",
                new_callable=AsyncMock,
                return_value=(Decimal("1"), "2026-10-09 12:00:00 UTC"),
            ),
            patch(
                "handlers.draw.fetch_wallet_mcn_balance",
                new_callable=AsyncMock,
                return_value=Decimal("9"),
            ),
            patch("handlers.draw.register_draw_wallet", new_callable=AsyncMock) as register,
        ):
            await draw.receive_wallet_for_draw(message, state)

        register.assert_not_awaited()
        self.assertIn("INSUFFICIENT MCN BALANCE", message.answer.await_args.args[0])

    async def test_temporary_rpc_failure_is_distinguished_from_low_balance(self):
        from handlers.market_data import MarketDataError

        message = self.make_message("0x1234567890abcdef1234567890abcdef12345678")
        state = SimpleNamespace(get_data=AsyncMock(return_value={}), clear=AsyncMock())
        with (
            patch(
                "handlers.draw.fetch_mcn_price_usd",
                new_callable=AsyncMock,
                side_effect=MarketDataError("provider unavailable"),
            ),
            patch("handlers.draw.register_draw_wallet", new_callable=AsyncMock) as register,
        ):
            await draw.receive_wallet_for_draw(message, state)

        register.assert_not_awaited()
        self.assertIn("Temporary verification error", message.answer.await_args.args[0])
        self.assertIn("send the same public address again", message.answer.await_args.args[0])
        state.clear.assert_not_awaited()

    async def test_draw_test_mode_performs_live_checks_without_creating_entry(self):
        wallet = "0x1234567890abcdef1234567890abcdef12345678"
        message = self.make_message(wallet)
        state = SimpleNamespace(
            get_data=AsyncMock(return_value={"draw_test_mode": True}),
            clear=AsyncMock(),
        )
        with (
            patch.object(draw, "MCN_OWNER_ID", 123),
            patch.object(draw, "MCN_TESTER_IDS", frozenset()),
            patch(
                "handlers.draw.fetch_mcn_price_usd",
                new_callable=AsyncMock,
                return_value=(Decimal("1"), "2026-10-09 12:00:00 UTC"),
            ),
            patch(
                "handlers.draw.fetch_wallet_mcn_balance",
                new_callable=AsyncMock,
                return_value=Decimal("10"),
            ),
            patch("handlers.draw.register_draw_wallet", new_callable=AsyncMock) as register,
        ):
            await draw.receive_wallet_for_draw(message, state)

        self.assertIn("TEST ELIGIBILITY PASS", message.answer.await_args.args[0])
        self.assertIn("No contest entry was created", message.answer.await_args.args[0])
        register.assert_not_awaited()
        state.clear.assert_awaited_once()

    async def test_draw_test_mode_is_restricted_to_private_configured_testers(self):
        message = self.make_message("/drawtest", user_id=124)
        state = SimpleNamespace(set_state=AsyncMock(), update_data=AsyncMock())
        with (
            patch.object(draw, "MCN_OWNER_ID", 123),
            patch.object(draw, "MCN_TESTER_IDS", frozenset()),
        ):
            await draw.start_draw_test(message, state)

        state.set_state.assert_not_awaited()
        self.assertIn("restricted", message.answer.await_args.args[0])

    async def test_admin_participant_view_is_never_loaded_for_non_owner(self):
        message = self.make_message("/drawadmin")
        with (
            patch.object(draw, "MCN_OWNER_ID", 999),
            patch("handlers.draw.get_draw_registrations", new_callable=AsyncMock) as get_rows,
        ):
            await draw.open_draw_admin(message)

        get_rows.assert_not_awaited()
        self.assertIn("not available", message.answer.await_args.args[0])

    async def test_owner_can_export_csv_but_other_users_cannot(self):
        participant = (
            42,
            "0x1234567890abcdef1234567890abcdef12345678",
            "2026-10-09 12:00:00 UTC",
            "20",
            12.0,
            0.6,
            1,
            None,
            None,
            None,
            None,
            None,
        )
        owner_message = SimpleNamespace(
            chat=SimpleNamespace(type="private"),
            answer_document=AsyncMock(),
        )
        owner_callback = SimpleNamespace(
            message=owner_message,
            from_user=SimpleNamespace(id=123),
            data="drawadmin:export",
            answer=AsyncMock(),
        )
        with (
            patch.object(draw, "MCN_OWNER_ID", 123),
            patch(
                "handlers.draw.get_draw_registrations",
                new_callable=AsyncMock,
                return_value=[participant],
            ) as get_rows,
        ):
            await draw.draw_admin_action(owner_callback)

        get_rows.assert_awaited_once()
        exported_file = owner_message.answer_document.await_args.args[0]
        self.assertEqual(exported_file.filename, "mcn_draw_participants.csv")

        stranger_message = SimpleNamespace(chat=SimpleNamespace(type="private"))
        stranger_callback = SimpleNamespace(
            message=stranger_message,
            from_user=SimpleNamespace(id=124),
            data="drawadmin:export",
            answer=AsyncMock(),
        )
        with (
            patch.object(draw, "MCN_OWNER_ID", 123),
            patch(
                "handlers.draw.get_draw_registrations",
                new_callable=AsyncMock,
            ) as get_rows,
        ):
            await draw.draw_admin_action(stranger_callback)

        get_rows.assert_not_awaited()
        stranger_callback.answer.assert_awaited_once()

    async def test_profile_artwork_changes_with_energy_rank(self):
        user = SimpleNamespace(id=456, username="guardian", first_name="Guardian")
        for (_, energy), artwork in zip(db.RANKS, RANK_ARTWORK):
            data = [None] * 19
            data[0] = user.id
            data[1] = user.username
            data[2] = energy
            data[5] = 0
            data[6] = 0
            data[7] = user.first_name
            data[9] = 0
            data[18] = "2026-10-09"
            with (
                patch("handlers.profile.ensure_user", new_callable=AsyncMock),
                patch("handlers.profile.get_user", new_callable=AsyncMock, return_value=tuple(data)),
                patch("handlers.profile.send_screen", new_callable=AsyncMock) as send_screen,
            ):
                await show_profile(SimpleNamespace(), user)
            self.assertEqual(send_screen.await_args.args[3], artwork)

    async def test_owner_private_admin_panel_lists_participants_and_admin_buttons(self):
        user = SimpleNamespace(id=123, username="owner", first_name="Owner")
        message = SimpleNamespace(
            from_user=user,
            chat=SimpleNamespace(type="private"),
            answer=AsyncMock(),
        )
        participant = (
            42,
            "0x1234567890abcdef1234567890abcdef12345678",
            "2026-10-09 12:00:00 UTC",
            "20",
            12.0,
            0.6,
            1,
            None,
            None,
            None,
            None,
            None,
        )
        with (
            patch.object(draw, "MCN_OWNER_ID", 123),
            patch(
                "handlers.draw.get_draw_registrations",
                new_callable=AsyncMock,
                return_value=[participant],
            ),
        ):
            await draw.open_draw_admin(message)

        replies = [call.args[0] for call in message.answer.await_args_list]
        self.assertTrue(any("Registered participants: 1" in reply for reply in replies))
        self.assertTrue(any(participant[1] in reply for reply in replies))
        markup = message.answer.await_args_list[-1].kwargs["reply_markup"]
        callbacks = {
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
        }
        self.assertIn("drawadmin:export", callbacks)
        self.assertIn("drawadmin:recheck", callbacks)


if __name__ == "__main__":
    unittest.main()
