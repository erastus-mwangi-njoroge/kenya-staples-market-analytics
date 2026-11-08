"""Central configuration: sources, thresholds and paths. Change thresholds here, not in code."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- Public sources (see docs/data_sources.md) --------------------------------------------
# HDX CKAN API is used to resolve the current CSV download link, because HDX resource URLs change.
HDX_PACKAGE_API = "https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-kenya"
FAOSTAT_QCL_URL = (
    "https://bulks-faostat.fao.org/production/"
    "Production_Crops_Livestock_E_All_Data_(Normalized).zip"
)
WB_CPI_URL = "https://api.worldbank.org/v2/country/KEN/indicator/FP.CPI.TOTL?format=json&per_page=200"

# --- Analytical parameters -----------------------------------------------------------------
FOCUS_COMMODITY = "Maize"          # commodity_group used for headline analysis
FAOSTAT_ITEM = "Maize"             # substring matched against FAOSTAT "Item"
SPIKE_THRESHOLD = 1.20             # price > 120% of trailing 12-month mean => spike
OUTLIER_MAD_Z = 6.0                # modified z-score on rolling-median residuals
MIN_SERIES_COVERAGE = 0.50         # share of months present between first and last obs
MIN_MONTHS_FOR_MARKET_STATS = 24
SUPPLY_SHOCK_THRESHOLD = -0.15     # production YoY at or below this = supply shock
KENYA_BBOX = {"lat": (-4.9, 5.2), "lon": (33.8, 42.0)}

REQUIRED_WFP_COLUMNS = [
    "date", "admin1", "admin2", "market", "latitude", "longitude", "category",
    "commodity", "unit", "priceflag", "pricetype", "currency", "price", "usdprice",
]


@dataclass
class Paths:
    """All input/output locations; injectable so tests can run in a temp directory."""
    data_dir: Path = ROOT / "data"
    out_dir: Path = ROOT / "outputs"

    @property
    def raw(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed(self) -> Path:
        return self.data_dir / "processed"

    @property
    def figures(self) -> Path:
        return self.out_dir / "figures"

    def ensure(self) -> "Paths":
        for p in (self.raw, self.processed, self.out_dir, self.figures):
            p.mkdir(parents=True, exist_ok=True)
        return self
