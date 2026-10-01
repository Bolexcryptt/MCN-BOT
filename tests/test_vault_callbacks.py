import asyncio
import unittest

from handlers import vault
from handlers.navigation import back_keyboard


class VaultCallbackButtonTest(unittest.TestCase):
    def test_back_button_returns_to_home_navigation(self):
        button = back_keyboard().inline_keyboard[0][0]

        self.assertEqual(button.text, "⬅️ Back")
        self.assertEqual(button.callback_data, "navigation:home")

    def test_vault_question_uses_inline_callback_buttons(self):
        class FakeUser:
            id = 42

        class FakeMessage:
            def __init__(self):
                self.from_user = FakeUser()
                self.sent = []

            async def answer(self, *args, **kwargs):
                self.sent.append((args, kwargs))

        msg = FakeMessage()
        vault.vault_users[msg.from_user.id] = 0

        asyncio.run(vault.send_vault_question(msg))

        self.assertTrue(msg.sent)
        reply_markup = msg.sent[-1][1]["reply_markup"]
        self.assertEqual(reply_markup.__class__.__name__, "InlineKeyboardMarkup")
        self.assertTrue(reply_markup.inline_keyboard)
        self.assertTrue(reply_markup.inline_keyboard[0][0].callback_data.startswith("answer:"))


if __name__ == "__main__":
    unittest.main()
