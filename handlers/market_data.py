import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.request import Request, urlopen

TOKEN_ADDRESS = "0x8e627241838b660cc90f96601952dcd7f47b7831"
POOL_ADDRESS = "0xc3688a53e99af856fac2a43bd470eb7dd1b0668f"
BASE_RPC_URL = "https://mainnet.base.org"
GECKOTERMINAL_POOL_URL = (
    f"https://api.geckoterminal.com/api/v2/networks/base/pools/{POOL_ADDRESS}"
)

logger = logging.getLogger(__name__)


class MarketDataError(Exception):
    """Raised when public market or Base RPC data cannot be read."""


def _request_json(url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "MCN-Kingdom-Bot/1.0",
        },
        method="POST" if data is not None else "GET",
    )
    try:
        with urlopen(request, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MarketDataError(f"Data provider request failed: {exc}") from exc
    if not isinstance(result, dict):
        raise MarketDataError("Data provider returned an unexpected response.")
    return result


def _as_usd(value: object) -> str:
    if value is None:
        return "Unavailable from current data source"
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "Unavailable from current data source"
    if not amount.is_finite():
        return "Unavailable from current data source"
    return f"${amount:,.8f}" if amount < 0.01 else f"${amount:,.2f}"


def _as_count(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def fetch_live_metrics() -> dict[str, str]:
    response = await asyncio.to_thread(_request_json, GECKOTERMINAL_POOL_URL)
    try:
        attributes = response["data"]["attributes"]
    except (KeyError, TypeError) as exc:
        raise MarketDataError("GeckoTerminal returned no MCN pool metrics.") from exc
    if not isinstance(attributes, dict):
        raise MarketDataError("GeckoTerminal returned malformed MCN pool metrics.")

    transactions = (attributes.get("transactions") or {}).get("h24") or {}
    buys = _as_count(transactions.get("buys"))
    sells = _as_count(transactions.get("sells"))
    if buys is None or sells is None:
        transaction_count = "Unavailable from current data source"
    else:
        transaction_count = f"{buys + sells:,} (Buys: {buys:,} · Sells: {sells:,})"

    market_cap = attributes.get("market_cap_usd")
    if market_cap is None:
        market_cap_text = "Unavailable (provider reports no market cap)"
    else:
        market_cap_text = _as_usd(market_cap)
    volume = attributes.get("volume_usd") or {}

    return {
        "price": _as_usd(attributes.get("base_token_price_usd")),
        "liquidity": _as_usd(attributes.get("reserve_in_usd")),
        "holders": "Unavailable from this pool-data source",
        "volume": _as_usd(volume.get("h24")),
        "transactions": transaction_count,
        "market_cap": market_cap_text,
        "fdv": _as_usd(attributes.get("fdv_usd")),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def _rpc_eth_call(selector: str) -> str:
    response = _request_json(
        BASE_RPC_URL,
        {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": TOKEN_ADDRESS, "data": selector}, "latest"],
            "id": 1,
        },
    )
    if response.get("error"):
        raise MarketDataError("Base RPC rejected an MCN contract read.")
    result = response.get("result")
    if not isinstance(result, str) or not result.startswith("0x"):
        raise MarketDataError("Base RPC returned no MCN contract value.")
    return result


def _load_contract_facts() -> dict[str, str]:
    try:
        raw_supply = int(_rpc_eth_call("0x18160ddd"), 16)
        decimals = int(_rpc_eth_call("0x313ce567"), 16)
        owner_result = _rpc_eth_call("0x8da5cb5b")
    except (ValueError, OverflowError) as exc:
        raise MarketDataError("Base RPC returned an invalid MCN contract value.") from exc

    if decimals > 36:
        raise MarketDataError("MCN contract returned an unsupported decimals value.")
    owner = "0x" + owner_result[2:].rjust(64, "0")[-40:]
    if len(owner_result) < 42:
        raise MarketDataError("Base RPC returned a malformed owner address.")

    supply = Decimal(raw_supply) / (Decimal(10) ** decimals)
    ownership = (
        "Renounced (owner() returns the zero address)"
        if int(owner[2:], 16) == 0
        else f"NOT renounced — owner(): {owner}"
    )
    return {
        "supply": f"{supply:,.{min(decimals, 8)}f}".rstrip("0").rstrip("."),
        "decimals": str(decimals),
        "ownership": ownership,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


async def fetch_contract_facts() -> dict[str, str]:
    return await asyncio.to_thread(_load_contract_facts)


def _fetch_wallet_balance(wallet: str) -> Decimal:
    wallet = wallet.strip()
    if not wallet.startswith("0x") or len(wallet) != 42:
        raise MarketDataError("Invalid wallet address format.")
    response = _request_json(
        "https://api.geckoterminal.com/api/v2/networks/base/address/" + wallet,
        None,
    )
    token_balances = response.get("data") or {}
    if isinstance(token_balances, dict):
        token_balances = token_balances.get("attributes", {}).get("token_balances", [])
    if not isinstance(token_balances, list):
        raise MarketDataError("Wallet token data was not available.")
    for item in token_balances:
        if not isinstance(item, dict):
            continue
        address = str(item.get("address", "")).casefold()
        if address == TOKEN_ADDRESS.casefold():
            qty = item.get("balance")
            try:
                return Decimal(str(qty))
            except (InvalidOperation, ValueError):
                return Decimal("0")
    return Decimal("0")


async def fetch_wallet_mcn_balance(wallet: str) -> Decimal:
    return await asyncio.to_thread(_fetch_wallet_balance, wallet)
