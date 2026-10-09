import unittest
from unittest.mock import patch

from handlers.market_data import (
    _load_contract_facts,
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


if __name__ == "__main__":
    unittest.main()
