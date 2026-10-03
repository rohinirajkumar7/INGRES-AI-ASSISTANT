"""Convert the raw INGRES Excel export into the slim CSV the API loads.

Usage (needs pandas + openpyxl, dev only):
    python scripts/build_dataset.py [path/to/ingres-data.xlsx]

The raw sheet has multi-level headers where every measure is split into
C / NC / PQ / Total columns. The chatbot needs the *Total* column of each
measure, which sit at these fixed positions in the 'GEC' sheet.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "source" / "ingres-data.xlsx"
OUT = ROOT / "ingres" / "data" / "groundwater.csv"

# column index in the raw sheet -> output column
COLUMNS = {
    1: "state",
    2: "district",
    7: "rainfall_mm",
    13: "area_ha",
    85: "recharge_ham",
    93: "extractable_ham",
    109: "extraction_ham",
    113: "stage_pct",
    121: "net_availability_ham",
}


def main() -> None:
    raw = pd.read_excel(SRC, sheet_name="GEC", header=None)
    df = raw.iloc[10:, list(COLUMNS)].copy()
    df.columns = list(COLUMNS.values())
    df = df[df["state"].notna() & df["district"].notna()]
    df["state"] = df["state"].astype(str).str.strip().str.upper()
    df["district"] = df["district"].astype(str).str.strip().str.upper()
    df = df[(df["state"] != "") & (df["district"] != "")]
    for col in list(COLUMNS.values())[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # 0 rainfall / 0 extractable resource means "not reported" in this export
    df.loc[df["rainfall_mm"] <= 0, "rainfall_mm"] = None
    df.loc[df["extractable_ham"] <= 0, ["stage_pct", "extraction_ham"]] = None
    df = df.round(2).sort_values(["state", "district"]).reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"wrote {len(df)} rows -> {OUT}")


if __name__ == "__main__":
    main()
