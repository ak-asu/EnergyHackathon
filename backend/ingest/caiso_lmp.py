"""CAISO OASIS LMP ingest — Palo Verde, SP15, NP15.

Uses OASIS `SingleZip` for `PRC_INTVL_LMP` and parses the returned ZIP+CSV.
Falls back to static values if OASIS is unavailable or returns unexpected data.
"""
import csv
import io
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx

_MOCK_LMP = {
    "PALOVRDE_ASR-APND": 38.50,
    "SP15": 42.30,
    "NP15": 40.10,
}

_NODE_ALIASES = {
    "SP15": "TH_SP15_GEN-APND",
    "NP15": "TH_NP15_GEN-APND",
}

_COMPONENT_TYPES = {"MCE", "MCC", "MCL"}
_DIRECT_TYPES = {"LMP"}

CAISO_URL = "https://oasis.caiso.com/oasisapi/SingleZip"


def _window_utc() -> tuple[str, str]:
    """Return a stable, recently published 1-hour UTC window for OASIS queries."""
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    fmt = "%Y%m%dT%H:%M-0000"
    return start.strftime(fmt), end.strftime(fmt)


def _parse_singlezip_csv(content: bytes) -> list[dict[str, str]]:
    """Parse CAISO SingleZip bytes into CSV rows."""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        csv_name = next((n for n in zf.namelist() if n.lower().endswith(".csv")), None)
        if not csv_name:
            raise ValueError("No CSV file found in OASIS zip payload")
        raw = zf.read(csv_name)
    text = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8", newline="")
    return list(csv.DictReader(text))


def _extract_latest_lmp(rows: list[dict[str, str]], *, caiso_node: str | None = None) -> float:
    """Extract the latest interval LMP from component or direct LMP rows."""
    by_interval: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for row in rows:
        if caiso_node:
            row_node = row.get("NODE") or row.get("NODE_ID") or row.get("NODE_ID_XML")
            if row_node != caiso_node:
                continue

        interval = row.get("INTERVALENDTIME_GMT") or row.get("INTERVALSTARTTIME_GMT")
        lmp_type = (row.get("LMP_TYPE") or "").upper()
        if not interval or not lmp_type:
            continue

        try:
            value = float(row.get("MW", ""))
        except (TypeError, ValueError):
            continue

        if lmp_type in _DIRECT_TYPES or lmp_type in _COMPONENT_TYPES:
            by_interval[interval][lmp_type] += value

    if not by_interval:
        raise ValueError("No usable LMP rows found in OASIS CSV")

    latest = sorted(by_interval.keys())[-1]
    bucket = by_interval[latest]

    if "LMP" in bucket:
        return bucket["LMP"]

    comp = sum(bucket.get(k, 0.0) for k in _COMPONENT_TYPES)
    if comp == 0.0 and bucket:
        comp = sum(bucket.values())
    return comp


async def fetch_lmp(node: str = "PALOVRDE_ASR-APND") -> dict:
    """Return latest 5-minute RTM LMP for a CAISO node.

    On any parsing/network/data error, falls back to static values.
    """
    request_node = node
    caiso_node = _NODE_ALIASES.get(request_node, request_node)
    fallback = _MOCK_LMP.get(request_node, 38.50)
    source = "CAISO_OASIS"
    try:
        start, end = _window_utc()
        params = {
            "resultformat": "6",
            "queryname": "PRC_INTVL_LMP",
            "version": "1",
            "market_run_id": "RTM",
            "node": caiso_node,
            "startdatetime": start,
            "enddatetime": end,
        }

        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.get(CAISO_URL, params=params)
            resp.raise_for_status()
            rows = _parse_singlezip_csv(resp.content)
            price = round(_extract_latest_lmp(rows, caiso_node=caiso_node), 5)
    except Exception:
        price = fallback
        source = "CAISO_OASIS_fallback"

    return {
        "node": request_node,
        "caiso_node": caiso_node,
        "lmp_mwh": price,
        "market": "CAISO RTM",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }


async def fetch_all_nodes() -> dict:
    request_nodes = list(_MOCK_LMP.keys())
    caiso_nodes = [_NODE_ALIASES.get(node, node) for node in request_nodes]

    start, end = _window_utc()
    params = {
        "resultformat": "6",
        "queryname": "PRC_INTVL_LMP",
        "version": "1",
        "market_run_id": "RTM",
        "node": ",".join(caiso_nodes),
        "startdatetime": start,
        "enddatetime": end,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(CAISO_URL, params=params)
            resp.raise_for_status()
            rows = _parse_singlezip_csv(resp.content)
    except Exception:
        return {
            node: {
                "node": node,
                "caiso_node": _NODE_ALIASES.get(node, node),
                "lmp_mwh": _MOCK_LMP.get(node, 38.50),
                "market": "CAISO RTM",
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                "source": "CAISO_OASIS_fallback",
            }
            for node in request_nodes
        }

    results = {}
    for node in request_nodes:
        caiso_node = _NODE_ALIASES.get(node, node)
        fallback = _MOCK_LMP.get(node, 38.50)
        source = "CAISO_OASIS"
        try:
            price = round(_extract_latest_lmp(rows, caiso_node=caiso_node), 5)
        except Exception:
            price = fallback
            source = "CAISO_OASIS_fallback"

        results[node] = {
            "node": node,
            "caiso_node": caiso_node,
            "lmp_mwh": price,
            "market": "CAISO RTM",
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": source,
        }

    return results
