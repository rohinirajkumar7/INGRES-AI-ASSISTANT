"""Dataset loading, categories and aggregation. Pure stdlib, no pandas."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

DATA_FILE = Path(__file__).resolve().parent / "data" / "groundwater.csv"

# --- official CGWB categories (stage of extraction, %) -----------------------
CATEGORY_LABELS = {
    "safe": "Safe",
    "semi_critical": "Semi-critical",
    "critical": "Critical",
    "over_exploited": "Over-exploited",
    "no_data": "No data",
}
CATEGORY_COLORS = {
    "safe": "#2e9e6a",
    "semi_critical": "#e5b53a",
    "critical": "#e8833a",
    "over_exploited": "#d64545",
    "no_data": "#9aa3b2",
}
CATEGORY_ORDER = ["safe", "semi_critical", "critical", "over_exploited", "no_data"]

# user-facing metric -> (district field, state aggregate field, label, unit)
METRICS = {
    "rainfall": ("rainfall", "avg_rainfall", "rainfall", "mm"),
    "extraction": ("stage", "stage", "stage of groundwater extraction", "%"),
    "recharge": ("recharge", "total_recharge", "annual groundwater recharge", "ham"),
    "availability": ("net", "total_net", "net groundwater availability", "ham"),
}


def category_for(stage: Optional[float]) -> str:
    if stage is None:
        return "no_data"
    if stage <= 70:
        return "safe"
    if stage <= 90:
        return "semi_critical"
    if stage <= 100:
        return "critical"
    return "over_exploited"


def display_name(raw: str) -> str:
    """'TAMILNADU' -> 'Tamil Nadu', 'ANDAMAN AND NICOBAR ISLANDS' -> proper case."""
    fixes = {"TAMILNADU": "Tamil Nadu", "LAKSHDWEEP": "Lakshadweep"}
    if raw in fixes:
        return fixes[raw]
    out = raw.title()
    for small in (" And ", " Of "):
        out = out.replace(small, small.lower())
    return out


def _num(value: str) -> Optional[float]:
    try:
        return float(value) if value not in ("", None) else None
    except ValueError:
        return None


class District:
    __slots__ = ("state_raw", "name_raw", "state", "name", "rainfall", "area",
                 "recharge", "extractable", "extraction", "stage", "net")

    def __init__(self, row: Dict[str, str]):
        self.state_raw = row["state"]
        self.name_raw = row["district"]
        self.state = display_name(self.state_raw)
        self.name = display_name(self.name_raw)
        self.rainfall = _num(row.get("rainfall_mm"))
        self.area = _num(row.get("area_ha"))
        self.recharge = _num(row.get("recharge_ham"))
        self.extractable = _num(row.get("extractable_ham"))
        self.extraction = _num(row.get("extraction_ham"))
        self.stage = _num(row.get("stage_pct"))
        self.net = _num(row.get("net_availability_ham"))

    @property
    def category(self) -> str:
        return category_for(self.stage)

    def row(self) -> dict:
        """Compact card/table representation sent to the frontend."""
        return {
            "name": self.name,
            "subtitle": self.state,
            "rainfall": _r(self.rainfall, 1),
            "extraction_stage": _r(self.stage, 1),
            "gw_recharge": _r(self.recharge, 0),
            "net_availability": _r(self.net, 0),
            "category": self.category,
            "category_label": CATEGORY_LABELS[self.category],
        }


def _r(value: Optional[float], digits: int) -> Optional[float]:
    return None if value is None else round(value, digits)


def aggregate(districts: List[District]) -> dict:
    """State / country level numbers.

    * stage is *weighted* (total extraction / total extractable), not a mean of
      district percentages.
    * rainfall is the area-weighted mean over districts that report it.
    """
    n = len(districts)
    ext_total = sum(d.extraction or 0 for d in districts if d.extractable)
    extractable_total = sum(d.extractable or 0 for d in districts if d.extractable)
    stage = round(ext_total / extractable_total * 100, 2) if extractable_total else None

    rain = [(d.rainfall, d.area or 0) for d in districts if d.rainfall]
    wsum = sum(a for _, a in rain)
    if rain and wsum:
        avg_rain = sum(r * a for r, a in rain) / wsum
    elif rain:
        avg_rain = sum(r for r, _ in rain) / len(rain)
    else:
        avg_rain = None

    counts = {c: 0 for c in CATEGORY_ORDER}
    for d in districts:
        counts[d.category] += 1

    return {
        "n_districts": n,
        "avg_rainfall": _r(avg_rain, 1),
        "total_recharge": _r(sum(d.recharge or 0 for d in districts), 0),
        "total_extractable": _r(extractable_total, 0),
        "total_extraction": _r(ext_total, 0),
        "total_net": _r(sum(d.net or 0 for d in districts), 0),
        "stage": stage,
        "category": category_for(stage),
        "counts": counts,
    }


class Store:
    def __init__(self, districts: List[District]):
        self.districts = districts
        self.by_state: Dict[str, List[District]] = {}
        for d in districts:
            self.by_state.setdefault(d.state, []).append(d)
        self.states = sorted(self.by_state)
        self._state_agg = {s: aggregate(v) for s, v in self.by_state.items()}
        self._india = aggregate(districts)

    # -- lookups --------------------------------------------------------
    def state_summary(self, state: str) -> Optional[dict]:
        return self._state_agg.get(state)

    def india_summary(self) -> dict:
        return self._india

    def districts_of(self, state: str) -> List[District]:
        return self.by_state.get(state, [])

    def find_district(self, state: str, name: str) -> Optional[District]:
        for d in self.by_state.get(state, []):
            if d.name == name:
                return d
        return None

    # -- rankings -------------------------------------------------------
    def rank_districts(self, metric: str, order: str = "desc", limit: int = 5,
                       state: Optional[str] = None, category: Optional[str] = None):
        """Return (total matching, top `limit` districts)."""
        field = METRICS[metric][0]
        pool = self.by_state.get(state, []) if state else self.districts
        if category:
            pool = [d for d in pool if d.category == category]
        pool = [d for d in pool if getattr(d, field) is not None]
        pool = sorted(pool, key=lambda d: getattr(d, field), reverse=(order == "desc"))
        return len(pool), pool[:limit]

    def rank_states(self, metric: str, order: str = "desc", limit: int = 5):
        field = METRICS[metric][1]
        items = [(s, a) for s, a in self._state_agg.items() if a.get(field) is not None]
        items.sort(key=lambda x: x[1][field], reverse=(order == "desc"))
        return len(items), items[:limit]


def load_store(path: Optional[Path] = None) -> Store:
    with open(path or DATA_FILE, newline="", encoding="utf-8") as fh:
        rows = [District(r) for r in csv.DictReader(fh) if r.get("state") and r.get("district")]
    if not rows:
        raise RuntimeError("Dataset is empty")
    return Store(rows)


@lru_cache(maxsize=1)
def get_store() -> Store:
    return load_store()
