import unittest
from unittest.mock import patch

from handlers.market_data import (
    MarketDataError,
    _fetch_mcn_price_usd,
    _fetch_wallet_balance,
    _load_contract_facts,
    _rpc_eth_call,
    fetch_live_metrics,
)


class MarketDataTest(unittest.IsolatedAsyncioTestCase):
    async def test_geckoterminal_market_metrics_are_parsed_without_inventing_data(self):
        response = {
            "data": {
                "attributes": {
                    "base_token_price_usd": "0.00000703514436743503",
                    "reserve_in_usd": "5980.2654",
                    "transactions": {"h24": {"buys": 0, "sells": 1}},
                    "volume_usd": {"h24": "0.001759301444"},
                    "market_cap_usd": None,
                    "fdv_usd": "7035.144367",
                }
            }
        }
        with patch("handlers.market_data._request_json", return_value=response):
            metrics = await fetch_live_metrics()

        self.assertEqual(metrics["price"], "$0.00000704")
        self.assertEqual(metrics["liquidity"], "$5,980.27")
        self.assertEqual(metrics["holders"], "Unavailable from this pool-data source")
        self.assertEqual(metrics["transactions"], "1 (Buys: 0 · Sells: 1)")
        self.assertIn("Unavailable", metrics["market_cap"])
        self.assertEqual(metrics["fdv"], "$7,035.14")
        self.assertTrue(metrics["updated_at"].endswith("UTC"))

    def test_contract_facts_show_supply_and_nonzero_owner_from_base_rpc(self):
        supply = hex(1_000_000_000 * 10**18)
        owner = "0x000000000000000000000000636c3ea0763b55912ad5bf5b2acc6629c9148ee0"
        with patch(
            "handlers.market_data._rpc_eth_call",
            side_effect=(supply, "0x12", owner),
        ):
            facts = _load_contract_facts()

        self.assertEqual(facts["supply"], "1,000,000,000")
        self.assertEqual(facts["decimals"], "18")
        self.assertIn("NOT renounced", facts["ownership"])
        self.assertIn("0x636c3ea0763b55912ad5bf5b2acc6629c9148ee0", facts["ownership"])
        self.assertTrue(facts["updated_at"].endswith("UTC"))

    def test_contract_facts_only_report_renounced_for_zero_owner(self):
        supply = hex(1_000_000_000 * 10**18)
        zero_owner = "0x" + ("0" * 64)
        with patch(
            "handlers.market_data._rpc_eth_call",
            side_effect=(supply, "0x12", zero_owner),
        ):
            facts = _load_contract_facts()

        self.assertIn("Renounced", facts["ownership"])

    def test_wallet_balance_uses_base_token_contract_balance_of_and_decimals(self):
        wallet = "0x1234567890abcdef1234567890abcdef12345678"
        raw_balance = hex(25 * 10**18)
        with patch(
            "handlers.market_data._rpc_eth_call",
            side_effect=("0x12", raw_balance),
        ) as rpc_call:
            balance = _fetch_wallet_balance(wallet)

        self.assertEqual(str(balance), "25")
        rpc_call.assert_any_call("0x313ce567")
        rpc_call.assert_any_call("0x70a08231" + wallet[2:].rjust(64, "0"))

    def test_wallet_balance_rejects_malformed_address_without_rpc(self):
        with patch("handlers.market_data._rpc_eth_call") as rpc_call:
            with self.assertRaises(MarketDataError):
                _fetch_wallet_balance("0xnot-a-wallet")
        rpc_call.assert_not_called()

    def test_draw_price_uses_token_address_usd_price_from_geckoterminal(self):
        with patch(
            "handlers.market_data._request_json",
            return_value={"data": {"attributes": {"price_usd": "0.0000125"}}},
        ):
            price, updated_at = _fetch_mcn_price_usd()

        self.assertEqual(str(price), "0.0000125")
        self.assertTrue(updated_at.endswith("UTC"))

    def test_draw_price_rejects_missing_price_as_temporary_provider_error(self):
        with patch(
            "handlers.market_data._request_json",
            return_value={"data": {"attributes": {}}},
        ):
            with self.assertRaises(MarketDataError):
                _fetch_mcn_price_usd()

    def test_base_rpc_reads_fallback_provider_if_primary_is_unavailable(self):
        with (
            patch(
                "handlers.market_data._request_json",
                side_effect=(
                    MarketDataError("primary unavailable"),
                    {"result": "0x" + "1" * 64},
                ),
            ) as request_json,
            patch("handlers.market_data.logger.warning"),
        ):
            result = _rpc_eth_call("0x313ce567")

        self.assertEqual(result, "0x" + "1" * 64)
        self.assertEqual(request_json.call_count, 2)


if __name__ == "__main__":
    unittest.main()
