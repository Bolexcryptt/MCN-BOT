import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.types import InlineKeyboardMarkup

from handlers import invite, leaderboard, navigation, profile, vault
from handlers.navigation import _resolve_asset_path, home_keyboard


class AssetMappingTest(unittest.TestCase):
    def test_key_kingdom_and_vault_artworks_map_to_real_assets(self):
        self.assertTrue(_resolve_asset_path("Guardian Hub").endswith("kingdom1.png"))
        self.assertTrue(_resolve_asset_path("Vault Entrance").endswith("thevault.png"))
        self.assertTrue(_resolve_asset_path("Vault Trial").endswith("vault2.png"))
        self.assertTrue(_resolve_asset_path("Guardian Trials").endswith("kingdom4.png"))


class BackButtonCoverageTest(unittest.IsolatedAsyncioTestCase):
    def make_message(self, user_id=42):
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=user_id, username="guardian", first_name="Guardian"),
            sent=[],
        )

        async def answer(*args, **kwargs):
            message.sent.append((args, kwargs))

        message.answer = answer
        return message

    def assert_last_message_has_back(self, message):
        markup = message.sent[-1][1]["reply_markup"]
        self.assertIsInstance(markup, InlineKeyboardMarkup)
        self.assertEqual(markup.inline_keyboard[-1][0].callback_data, "navigation:home")

    async def test_guardian_hub_has_every_primary_destination(self):
        destinations = {
            button.callback_data
            for row in home_keyboard().inline_keyboard
            for button in row
        }
        self.assertEqual(
            destinations,
            {
                "hub:oria",
                "hub:guardians",
                "hub:mcn",
                "hub:live",
                "hub:verify",
                "hub:rewards",
                "hub:lore",
            },
        )

    async def test_profile_screen_has_back_button(self):
        message = self.make_message()
        with (
            patch("handlers.profile.ensure_user", new_callable=AsyncMock),
            patch("handlers.profile.get_user", new_callable=AsyncMock, return_value=(42, "guardian", 8, None, 0, 2, 1, "Guardian")),
        ):
            await profile.me(message)

        self.assert_last_message_has_back(message)

    async def test_leaderboard_screen_has_back_button(self):
        message = self.make_message()
        with (
            patch("handlers.leaderboard.ensure_user", new_callable=AsyncMock),
            patch("handlers.leaderboard.get_leaderboard", new_callable=AsyncMock, return_value=[("guardian", 8, 1)]),
        ):
            await leaderboard.leaderboard(message)

        self.assert_last_message_has_back(message)

    async def test_invite_screen_has_back_button(self):
        message = self.make_message()
        message.bot = SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(username="test_bot")))
        with (
            patch("handlers.invite.ensure_user", new_callable=AsyncMock),
            patch("handlers.invite.get_invite_stats", new_callable=AsyncMock, return_value=(2, 100)),
        ):
            await invite.invite(message)

        self.assert_last_message_has_back(message)

    async def test_vault_and_questions_keyboards_have_back_button(self):
        for keyboard in (
            vault.build_answer_keyboard(42, ["the vault grows", "guardians"]),
        ):
            self.assertEqual(keyboard.inline_keyboard[-1][0].callback_data, "navigation:home")

        self.assertEqual(
            vault.build_answer_keyboard(42, ["answer", "wrong"]).inline_keyboard[-1][0].text,
            "⬅️ Back",
        )

    async def test_guardians_screen_links_to_energy_earning_vault_and_trials(self):
        message = self.make_message()
        await navigation.show_guardians_screen(message, message.from_user)

        text = message.sent[-1][0][0]
        self.assertIn("5 questions, +5 Energy", text)
        self.assertIn("Unlimited Trials", text)
        keyboard = message.sent[-1][1]["reply_markup"]
        callbacks = {
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
        }
        self.assertIn("hub:vault", callbacks)
        self.assertIn("hub:trials", callbacks)

    async def test_vault_and_trials_buttons_dispatch_to_question_flows(self):
        message = self.make_message()
        callback = SimpleNamespace(
            message=message,
            data="hub:vault",
            from_user=message.from_user,
            answer=AsyncMock(),
        )
        with (
            patch("handlers.vault.show_vault", new_callable=AsyncMock) as show_vault,
            patch("handlers.vault.show_trials", new_callable=AsyncMock) as show_trials,
        ):
            await navigation.open_hub_section(callback)
            callback.data = "hub:trials"
            await navigation.open_hub_section(callback)

        show_vault.assert_awaited_once_with(message, message.from_user)
        show_trials.assert_awaited_once_with(message, message.from_user)


if __name__ == "__main__":
    unittest.main()