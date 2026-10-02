import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.types import InlineKeyboardMarkup

from handlers import invite, leaderboard, profile, vault
from handlers.navigation import home_keyboard


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
                "hub:vault",
                "hub:trials",
                "hub:profile",
                "hub:leaderboard",
                "hub:invite",
                "hub:daily",
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


if __name__ == "__main__":
    unittest.main()