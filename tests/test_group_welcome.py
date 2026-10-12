import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from handlers.group_welcome import (
    WELCOME_IMAGE,
    _is_admin_status,
    _welcome_keyboard,
    welcome_new_members,
    welcome_when_promoted,
)
from handlers import user


class GroupWelcomeTest(unittest.IsolatedAsyncioTestCase):
    def make_join_message(self, members):
        bot = SimpleNamespace(
            get_me=AsyncMock(return_value=SimpleNamespace(username="MaineCoonBot")),
            send_photo=AsyncMock(),
        )
        return SimpleNamespace(
            new_chat_members=members,
            chat=SimpleNamespace(id=-100123),
            bot=bot,
        )

    def make_update(self, old_status, new_status):
        bot = SimpleNamespace(
            get_me=AsyncMock(return_value=SimpleNamespace(username="MaineCoonBot")),
            send_photo=AsyncMock(),
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

    async def test_posts_image_welcome_on_admin_promotion_with_private_bot_links(self):
        update = self.make_update("member", "administrator")

        await welcome_when_promoted(update)

        update.bot.send_photo.assert_awaited_once()
        chat_id = update.bot.send_photo.await_args.args[0]
        self.assertEqual(chat_id, -100123)
        photo_call = update.bot.send_photo.await_args.kwargs
        self.assertEqual(Path(photo_call["photo"].path), WELCOME_IMAGE)
        caption = photo_call["caption"]
        self.assertIn("Welcome to the MCN Kingdom Portal", caption)
        self.assertIn("Welcome, Guardian!", caption)
        self.assertIn("MCN Hold Contest", caption)
        self.assertIn("/draw in my private chat", caption)
        self.assertIn("Never share your private key or seed phrase", caption)
        keyboard = photo_call["reply_markup"]
        buttons = [button for row in keyboard.inline_keyboard for button in row]
        self.assertTrue(any(button.url == "https://t.me/MaineCoonBot?start=kingdom" for button in buttons))
        self.assertTrue(any(button.url == "https://t.me/MaineCoonBot?start=draw" for button in buttons))

    async def test_welcomes_each_new_member_with_image_and_username_mention(self):
        member = SimpleNamespace(
            id=789,
            username="new_guardian",
            full_name="New Guardian",
            is_bot=False,
        )
        message = self.make_join_message([member])

        await welcome_new_members(message)

        message.bot.send_photo.assert_awaited_once()
        photo_call = message.bot.send_photo.await_args.kwargs
        self.assertEqual(photo_call["chat_id"], -100123)
        self.assertEqual(Path(photo_call["photo"].path), WELCOME_IMAGE)
        self.assertIn(
            '<a href="tg://user?id=789">@new_guardian</a>',
            photo_call["caption"],
        )
        self.assertEqual(photo_call["parse_mode"], "HTML")
        self.assertEqual(
            photo_call["reply_markup"],
            _welcome_keyboard("MaineCoonBot"),
        )

    async def test_welcomes_members_without_usernames_and_skips_bots(self):
        member_without_username = SimpleNamespace(
            id=790,
            username=None,
            full_name="Guardian <One>",
            is_bot=False,
        )
        bot_member = SimpleNamespace(
            id=791,
            username="community_bot",
            full_name="Community Bot",
            is_bot=True,
        )
        message = self.make_join_message([member_without_username, bot_member])

        await welcome_new_members(message)

        message.bot.send_photo.assert_awaited_once()
        caption = message.bot.send_photo.await_args.kwargs["caption"]
        self.assertIn(
            '<a href="tg://user?id=790">Guardian &lt;One&gt;</a>',
            caption,
        )
        self.assertNotIn("community_bot", caption)

    async def test_does_not_fetch_bot_details_when_only_bots_join(self):
        message = self.make_join_message(
            [SimpleNamespace(id=791, is_bot=True)]
        )

        await welcome_new_members(message)

        message.bot.get_me.assert_not_awaited()
        message.bot.send_photo.assert_not_awaited()

    async def test_does_not_welcome_when_not_promoted_to_admin(self):
        update = self.make_update("left", "member")

        await welcome_when_promoted(update)

        update.bot.get_me.assert_not_awaited()
        update.bot.send_photo.assert_not_awaited()

    async def test_does_not_post_duplicate_when_admin_role_changes(self):
        update = self.make_update("administrator", "creator")

        await welcome_when_promoted(update)

        update.bot.get_me.assert_not_awaited()
        update.bot.send_photo.assert_not_awaited()

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
