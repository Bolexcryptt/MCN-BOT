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
                "hub:leaderboard",
                "hub:notifications",
            },
        )

    async def test_notifications_screen_displays_hold_contest_and_official_links(self):
        message = self.make_message()
        await navigation.show_notifications_screen(message, message.from_user)

        text, options = message.sent[-1]
        text = text[0]
        self.assertIn("The MCN Hold Contest is back.", text)
        self.assertIn("Hold at least $10 of MCN on Base", text)
        self.assertIn("5 winners will be selected every week.", text)
        self.assertIn("Each winner receives $5 worth of ETH.", text)
        self.assertIn("Follow @MCN_MAINECOON", text)
        self.assertIn("Follow @KingStanny", text)
        self.assertIn("Buy & hold at least $10 of $MCN", text)
        buttons = [
            button
            for row in options["reply_markup"].inline_keyboard
            for button in row
        ]
        self.assertTrue(any(button.callback_data == "hub:rewards" for button in buttons))
        self.assertTrue(any(button.callback_data == "navigation:home" for button in buttons))

    async def test_profile_screen_has_back_button(self):
        message = self.make_message()
        with (
            patch("handlers.profile.ensure_user", new_callable=AsyncMock),
            patch("handlers.profile.get_user", new_callable=AsyncMock, return_value=(
                42, "guardian", 8, None, 0, 2, 1, "Guardian",
                "🐾 Guardian", 0, None, 0, None, None, None, None, None, None,
                "2026-10-08",
            )),
        ):
            await profile.me(message)

        self.assert_last_message_has_back(message)
        text = message.sent[-1][0][0]
        self.assertIn("Username: @guardian", text)
        self.assertIn("Rank: 🐾 Guardian", text)
        self.assertIn("Joined: 2026-10-08", text)
        self.assertIn("Guardian XP: 8", text)
        self.assertIn("Community activity", text)

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
        text = message.sent[-1][0][0]
        self.assertIn("https://t.me/test_bot?start=42", text)
        buttons = [
            button
            for row in message.sent[-1][1]["reply_markup"].inline_keyboard
            for button in row
        ]
        self.assertTrue(any(button.url == "https://t.me/test_bot?start=42" for button in buttons))
        self.assertTrue(any(button.url and button.url.startswith("https://t.me/share/url?") for button in buttons))

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
        self.assertIn("hub:leaderboard", callbacks)

    async def test_mcn_screen_renders_site_and_verify_buttons(self):
        message = self.make_message()
        await navigation.show_mcn_screen(message, message.from_user)

        text, options = message.sent[-1]
        self.assertIn("💎 MCN", text[0])
        buttons = [
            button
            for row in options["reply_markup"].inline_keyboard
            for button in row
        ]
        self.assertTrue(any(button.url == "https://mainecoonmcn.vercel.app/" for button in buttons))
        self.assertIn("hub:verify", {button.callback_data for button in buttons})

    async def test_rewards_screen_renders_leaderboard_profile_and_invite_buttons(self):
        message = self.make_message()
        await navigation.show_rewards_screen(message, message.from_user)

        text, options = message.sent[-1]
        self.assertIn("COMMUNITY & REWARDS", text[0])
        buttons = [
            button
            for row in options["reply_markup"].inline_keyboard
            for button in row
        ]
        callbacks = {button.callback_data for button in buttons}
        self.assertIn("hub:leaderboard", callbacks)
        self.assertIn("hub:profile", callbacks)
        self.assertIn("hub:invite", callbacks)


    async def test_verify_screen_shows_contract_lock_date_and_explorer_links(self):
        message = self.make_message()
        await navigation.show_verify_screen(message, message.from_user)

        text = message.sent[-1][0][0]
        self.assertIn("0x8e627241838b660cc90f96601952dcd7f47b7831", text)
        self.assertIn("August 10, 2027", text)
        self.assertIn("not a live guarantee", text)
        buttons = [
            button
            for row in message.sent[-1][1]["reply_markup"].inline_keyboard
            for button in row
        ]
        self.assertTrue(any(button.url and "basescan.org/token/" in button.url for button in buttons))
        self.assertTrue(any(button.url and "uncx.network/lockers/" in button.url for button in buttons))

    async def test_official_links_screen_has_all_requested_direct_links(self):
        message = self.make_message()
        await navigation.show_links_screen(message, message.from_user)

        buttons = [
            button
            for row in message.sent[-1][1]["reply_markup"].inline_keyboard
            for button in row
        ]
        urls = {button.url for button in buttons if button.url}
        self.assertEqual(
            urls,
            {
                "https://mainecoonmcn.vercel.app/",
                "https://www.geckoterminal.com/base/pools/0xc3688a53e99af856fac2a43bd470eb7dd1b0668f",
                "https://dexscreener.com/base/0x8e627241838b660cc90f96601952dcd7f47b7831",
                "https://www.dextools.io/app/base/pair-explorer/0xc3688a53e99af856fac2a43bd470eb7dd1b0668f",
                "https://basescan.org/token/0x8e627241838b660cc90f96601952dcd7f47b7831",
                "https://app.uncx.network/lockers/manage/lockers-v3?service=edit&chain=8453&wallet=0x636c3ea0763b55912ad5bf5b2acc6629c9148ee0&locker=0x231278edd38b00b07fbd52120cef685b9baebcc1&pool=0xaa64742981c606881c458e7d5cb8b108e4b60eb8&lock=1156&index=0",
            },
        )

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

    async def test_mcn_rewards_and_leaderboard_buttons_dispatch(self):
        message = self.make_message()
        callback = SimpleNamespace(
            message=message,
            data="hub:mcn",
            from_user=message.from_user,
            answer=AsyncMock(),
        )
        with patch.object(navigation, "show_mcn_screen", new_callable=AsyncMock) as show_mcn, \
             patch.object(navigation, "show_rewards_screen", new_callable=AsyncMock) as show_rewards, \
             patch.object(navigation, "show_notifications_screen", new_callable=AsyncMock) as show_notifications, \
             patch("handlers.leaderboard.show_leaderboard", new_callable=AsyncMock) as show_leaderboard:
            await navigation.open_hub_section(callback)
            callback.data = "hub:rewards"
            await navigation.open_hub_section(callback)
            callback.data = "hub:leaderboard"
            await navigation.open_hub_section(callback)
            callback.data = "hub:notifications"
            await navigation.open_hub_section(callback)

        show_mcn.assert_awaited_once_with(message, message.from_user)
        show_rewards.assert_awaited_once_with(message, message.from_user)
        show_leaderboard.assert_awaited_once_with(message, message.from_user)
        show_notifications.assert_awaited_once_with(message, message.from_user)


if __name__ == "__main__":
    unittest.main()