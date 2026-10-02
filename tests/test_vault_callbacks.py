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
        self.assertEqual(len(reply_markup.inline_keyboard), 3)
        self.assertLessEqual(
            max(len(row[0].callback_data.encode("utf-8")) for row in reply_markup.inline_keyboard),
            64,
        )

    def test_question_deck_is_lore_based_with_two_plausible_distinct_choices(self):
        self.assertGreaterEqual(len(vault.QUESTIONS), 50)
        self.assertEqual(len({question for question, _, _ in vault.QUESTIONS}), len(vault.QUESTIONS))

        for question, correct, wrong in vault.QUESTIONS:
            with self.subTest(question=question):
                self.assertTrue(any(term in question.casefold() for term in (
                    "oria", "guardian", "vault", "kingdom", "ambassador", "energy"
                )))
                self.assertNotEqual(correct.casefold(), wrong.casefold())
                self.assertLessEqual(abs(len(correct) - len(wrong)), 20)
                self.assertEqual(set(vault._answer_options(correct, wrong)), {correct, wrong})
                self.assertEqual(len(vault._answer_options(correct, wrong)), 2)
                self.assertLessEqual(
                    max(
                        len(button.callback_data.encode("utf-8"))
                        for row in vault.build_answer_keyboard(
                            1234567890123456789,
                            [correct, wrong],
                            token="abcdef",
                            correct_answer=correct,
                        ).inline_keyboard
                        for button in row
                    ),
                    64,
                )
                self.assertLessEqual(
                    max(
                        len(button.callback_data.encode("utf-8"))
                        for row in vault._daily_keyboard(
                            1234567890123456789,
                            "2026-10-02",
                            correct,
                            wrong,
                        ).inline_keyboard
                        for button in row
                    ),
                    64,
                )

        prompts = "\n".join(question for question, _, _ in vault.QUESTIONS)
        self.assertNotIn("2 + 2", prompts)
        self.assertNotIn("5 + 3", prompts)
        self.assertNotIn("10 - 4", prompts)


if __name__ == "__main__":
    unittest.main()
