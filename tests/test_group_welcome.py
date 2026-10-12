import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from handlers.group_welcome import (
    _is_admin_status,
    _welcome_keyboard,
    welcome_when_promoted,
)
from handlers import user


class GroupWelcomeTest(unittest.IsolatedAsyncioTestCase):
    def make_update(self, old_status, new_status):
        bot = SimpleNamespace(
            get_me=AsyncMock(return_value=SimpleNamespace(username="MaineCoonBot")),
            send_message=AsyncMock(),
        )
        return SimpleNamespace(
            old_chat_member=SimpleNamespace(status=old_status),
            new_chat_member=SimpleNamespace(status=new_status),
            chat=SimpleNamespace(id=-100123),
            bot=bot,
        )

    def test_only_admin_and_creator_statuses_are_admins(self):
        self.assertTrue(_is_admin_status("administrator"))
        self.assertTrue(_is_admin_status("creator"))
        self.assertFalse(_is_admin_status("member"))
        self.assertFalse(_is_admin_status("left"))

    async def test_posts_welcome_on_admin_promotion_with_private_bot_links(self):
        update = self.make_update("member", "administrator")

        await welcome_when_promoted(update)

        update.bot.send_message.assert_awaited_once()
        chat_id, text = update.bot.send_message.await_args.args
        self.assertEqual(chat_id, -100123)
        self.assertIn("Welcome to the MCN Kingdom Portal", text)
        self.assertIn("/draw in my private chat", text)
        self.assertIn("Never share a private key or seed phrase", text)
        keyboard = update.bot.send_message.await_args.kwargs["reply_markup"]
        buttons = [button for row in keyboard.inline_keyboard for button in row]
        self.assertTrue(any(button.url == "https://t.me/MaineCoonBot?start=kingdom" for button in buttons))
        self.assertTrue(any(button.url == "https://t.me/MaineCoonBot?start=draw" for button in buttons))

    async def test_does_not_welcome_when_not_promoted_to_admin(self):
        update = self.make_update("left", "member")

        await welcome_when_promoted(update)

        update.bot.get_me.assert_not_awaited()
        update.bot.send_message.assert_not_awaited()

    async def test_does_not_post_duplicate_when_admin_role_changes(self):
        update = self.make_update("administrator", "creator")

        await welcome_when_promoted(update)

        update.bot.get_me.assert_not_awaited()
        update.bot.send_message.assert_not_awaited()

    def test_buttons_open_private_bot_experience(self):
        keyboard = _welcome_keyboard("MaineCoonBot")
        urls = [button.url for row in keyboard.inline_keyboard for button in row]

        self.assertEqual(
            urls,
            [
                "https://t.me/MaineCoonBot?start=kingdom",
                "https://t.me/MaineCoonBot?start=draw",
            ],
        )

    async def test_draw_deep_link_opens_registration_screen(self):
        message = SimpleNamespace(
            text="/start draw",
            from_user=SimpleNamespace(id=456),
        )
        with (
            patch("handlers.user.ensure_user", new_callable=AsyncMock),
            patch(
                "handlers.draw.show_draw_screen",
                new_callable=AsyncMock,
            ) as show_draw,
            patch("handlers.user.send_home", new_callable=AsyncMock) as send_home,
        ):
            await user.start(message)

        show_draw.assert_awaited_once_with(message, message.from_user)
        send_home.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
