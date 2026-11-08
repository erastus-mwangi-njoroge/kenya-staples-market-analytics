"""Download public datasets and record provenance (URL, timestamp, checksum)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from .config import FAOSTAT_QCL_URL, HDX_PACKAGE_API, WB_CPI_URL, Paths

HEADERS = {"User-Agent": "kenya-staples-market-analytics/1.0 (portfolio project)"}


def _download(url: str, dest: Path, timeout: int = 180) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout, headers=HEADERS) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return dest


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _log_provenance(paths: Paths, name: str, url: str, file: Path) -> None:
    log = paths.raw / "_provenance.json"
    records = json.loads(log.read_text()) if log.exists() else {}
    records[name] = {
        "url": url,
        "file": file.name,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": file.stat().st_size,
        "sha256": _sha256(file),
    }
    log.write_text(json.dumps(records, indent=2))


def resolve_wfp_csv_url() -> str:
    """Ask the HDX API for the main CSV resource (skipping the small QuickCharts extract)."""
    meta = requests.get(HDX_PACKAGE_API, timeout=60, headers=HEADERS).json()
    for res in meta["result"]["resources"]:
        name = res.get("name", "").lower()
        if res.get("format", "").lower() == "csv" and "qc" not in name and "quickcharts" not in name:
            return res.get("download_url") or res["url"]
    raise RuntimeError("No suitable CSV resource found in the HDX package; check docs/data_sources.md")


def fetch_wfp_prices(paths: Paths) -> Path:
    url = resolve_wfp_csv_url()
    dest = _download(url, paths.raw / "wfp_food_prices_ken.csv")
    _log_provenance(paths, "wfp_food_prices_kenya", url, dest)
    return dest


def fetch_faostat_qcl(paths: Paths) -> Path:
    dest = _download(FAOSTAT_QCL_URL, paths.raw / "faostat_qcl_normalized.zip")
    _log_provenance(paths, "faostat_crops_livestock", FAOSTAT_QCL_URL, dest)
    return dest


def fetch_cpi(paths: Paths) -> Path | None:
    """Optional: World Bank CPI (2010=100) to compute real prices. Failure is non-fatal."""
    try:
        payload = requests.get(WB_CPI_URL, timeout=60, headers=HEADERS).json()
        rows = [{"year": int(r["date"]), "cpi": r["value"]} for r in payload[1] if r["value"] is not None]
        dest = paths.raw / "wb_cpi_kenya.csv"
        pd.DataFrame(rows).sort_values("year").to_csv(dest, index=False)
        _log_provenance(paths, "worldbank_cpi_kenya", WB_CPI_URL, dest)
        return dest
    except Exception as exc:  # noqa: BLE001 - optional enrichment must not break the pipeline
        print(f"[warn] CPI download skipped: {exc}")
        return None
