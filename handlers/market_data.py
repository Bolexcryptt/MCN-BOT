import asyncio
import json
import logging
import re
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
GECKOTERMINAL_TOKEN_URL = (
    f"https://api.geckoterminal.com/api/v2/networks/base/tokens/{TOKEN_ADDRESS}"
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


def _rpc_eth_call(selector: str, contract_address: str = TOKEN_ADDRESS) -> str:
    response = _request_json(
        BASE_RPC_URL,
        {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": contract_address, "data": selector}, "latest"],
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
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", wallet):
        raise MarketDataError("Invalid wallet address format.")
    try:
        decimals = int(_rpc_eth_call("0x313ce567"), 16)
        balance_data = "0x70a08231" + wallet[2:].lower().rjust(64, "0")
        raw_balance = int(_rpc_eth_call(balance_data), 16)
    except (ValueError, OverflowError) as exc:
        raise MarketDataError("Base RPC returned an invalid MCN balance.") from exc

    if decimals > 36:
        raise MarketDataError("MCN contract returned an unsupported decimals value.")
    return Decimal(raw_balance) / (Decimal(10) ** decimals)


async def fetch_wallet_mcn_balance(wallet: str) -> Decimal:
    return await asyncio.to_thread(_fetch_wallet_balance, wallet)


def _fetch_mcn_price_usd() -> tuple[Decimal, str]:
    response = _request_json(GECKOTERMINAL_TOKEN_URL)
    try:
        attributes = response["data"]["attributes"]
        price = Decimal(str(attributes["price_usd"]))
    except (KeyError, TypeError, InvalidOperation, ValueError) as exc:
        raise MarketDataError("GeckoTerminal did not return a current MCN/USD price.") from exc

    if not price.is_finite() or price <= 0:
        raise MarketDataError("GeckoTerminal returned an invalid MCN/USD price.")
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return price, updated_at


async def fetch_mcn_price_usd() -> tuple[Decimal, str]:
    return await asyncio.to_thread(_fetch_mcn_price_usd)
