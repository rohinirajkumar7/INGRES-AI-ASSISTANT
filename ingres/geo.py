"""Tile-grid map layout (no GeoJSON needed, works offline, tiny payload).

(row, col) positions roughly follow India's geography. Keys are the display
names produced by ingres.data.display_name().
"""

TILES = {
    "Jammu and Kashmir": ("JK", 0, 2), "Ladakh": ("LA", 0, 3),
    "Punjab": ("PB", 1, 2), "Himachal Pradesh": ("HP", 1, 3), "Uttarakhand": ("UK", 1, 4),
    "Chandigarh": ("CH", 2, 1), "Haryana": ("HR", 2, 2), "Delhi": ("DL", 2, 3),
    "Uttar Pradesh": ("UP", 2, 4), "Bihar": ("BR", 2, 5), "Sikkim": ("SK", 2, 6),
    "Arunachal Pradesh": ("AR", 2, 8),
    "Rajasthan": ("RJ", 3, 2), "Madhya Pradesh": ("MP", 3, 3), "Chhattisgarh": ("CG", 3, 4),
    "Jharkhand": ("JH", 3, 5), "West Bengal": ("WB", 3, 6), "Assam": ("AS", 3, 7),
    "Nagaland": ("NL", 3, 8),
    "Gujarat": ("GJ", 4, 2), "Maharashtra": ("MH", 4, 3), "Telangana": ("TG", 4, 4),
    "Odisha": ("OD", 4, 5), "Meghalaya": ("ML", 4, 7), "Manipur": ("MN", 4, 8),
    "Daman and Diu": ("DD", 5, 1), "Dadra and Nagar Haveli": ("DN", 5, 2), "Goa": ("GA", 5, 3),
    "Karnataka": ("KA", 5, 4), "Andhra Pradesh": ("AP", 5, 5), "Tripura": ("TR", 5, 7),
    "Mizoram": ("MZ", 5, 8),
    "Lakshadweep": ("LD", 6, 2), "Kerala": ("KL", 6, 3), "Tamil Nadu": ("TN", 6, 4),
    "Puducherry": ("PY", 6, 5),
    "Andaman and Nicobar Islands": ("AN", 7, 7),
}


def map_tiles(store) -> list:
    """One tile per state present in the dataset, with its stage category."""
    out = []
    for state in store.states:
        code, row, col = TILES.get(state, (state[:2].upper(), 8, 0))
        s = store.state_summary(state)
        out.append({
            "state": state, "code": code, "row": row, "col": col,
            "stage": s["stage"], "rainfall": s["avg_rainfall"], "category": s["category"],
        })
    return out
