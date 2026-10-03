"""Find / resolve state & district names (typo tolerant, alias aware)."""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .data import Store

# generic or very short district names that would cause false positives in free text
STOP_KEYS = {"east", "west", "north", "south", "central", "mon", "las", "kng", "bls", "ntr", "data"}

# words of a user query that must never be fuzzy-matched to a place
QUERY_WORDS = {
    "rainfall", "rain", "groundwater", "ground", "water", "extraction", "stage", "recharge",
    "availability", "available", "compare", "comparison", "between", "versus", "difference",
    "districts", "district", "states", "state", "india", "indian", "show", "tell", "about",
    "which", "highest", "lowest", "most", "least", "overexploited", "critical", "semi",
    "safe", "status", "information", "details", "please", "list", "what", "with", "from",
    "data", "average", "total", "annual", "net", "resource", "resources", "over", "exploited",
}

# alias (lowercase) -> (raw state, raw district)
DISTRICT_ALIASES: Dict[str, Tuple[str, str]] = {
    "bangalore": ("KARNATAKA", "BENGALURU (URBAN)"),
    "bengaluru": ("KARNATAKA", "BENGALURU (URBAN)"),
    "bangaluru": ("KARNATAKA", "BENGALURU (URBAN)"),
    "mysore": ("KARNATAKA", "MYSURU"),
    "belgaum": ("KARNATAKA", "BELAGAVI"),
    "bellary": ("KARNATAKA", "BALLARI"),
    "gulbarga": ("KARNATAKA", "KALBURGI"),
    "shimoga": ("KARNATAKA", "SHIVAMOGGA"),
    "tumkur": ("KARNATAKA", "TUMAKURU"),
    "mangalore": ("KARNATAKA", "DAKSHINA KANNADA"),
    "mumbai": ("MAHARASHTRA", "MUMBAI"),
    "bombay": ("MAHARASHTRA", "MUMBAI"),
    "madras": ("TAMILNADU", "CHENNAI"),
    "kolkata": ("WEST BENGAL", "KOLKATTA"),
    "calcutta": ("WEST BENGAL", "KOLKATTA"),
    "poona": ("MAHARASHTRA", "PUNE"),
    "gurgaon": ("HARYANA", "GURUGRAM"),
    "allahabad": ("UTTAR PRADESH", "PRAYAGRAJ"),
    "vizag": ("ANDHRA PRADESH", "VISAKHAPATNAM"),
    "baroda": ("GUJARAT", "VADODARA"),
    "trivandrum": ("KERALA", "THIRUVANANTHAPURAM"),
}
STATE_ALIASES: Dict[str, str] = {
    "tamilnadu": "TAMILNADU", "orissa": "ODISHA", "uttaranchal": "UTTARAKHAND",
    "jammu kashmir": "JAMMU AND KASHMIR", "j and k": "JAMMU AND KASHMIR",
    "nct of delhi": "DELHI", "new delhi": "DELHI", "andaman": "ANDAMAN AND NICOBAR ISLANDS",
    "pondicherry": "PUDUCHERRY", "lakshadweep": "LAKSHDWEEP",
}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower().replace("&", " and ")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Location:
    kind: str                       # 'state' | 'district' | 'country'
    state: Optional[str] = None     # display name
    district: Optional[str] = None  # display name
    also_in: List[str] = field(default_factory=list)  # other states with same district name

    @property
    def label(self) -> str:
        return self.district or self.state or "India"


class LocationIndex:
    def __init__(self, store: Store):
        self.store = store
        self.keys: Dict[str, List[Location]] = {}
        raw_to_state = {d.state_raw: d.state for d in store.districts}

        for state in store.states:
            self._add(norm(state), Location("state", state), allow_short=True)
        for alias, raw in STATE_ALIASES.items():
            if raw in raw_to_state:
                self._add(norm(alias), Location("state", raw_to_state[raw]), allow_short=True, override=True)

        for d in store.districts:
            loc = Location("district", d.state, d.name)
            self._add(norm(d.name), loc)
            bare = norm(re.sub(r"\(.*?\)", "", d.name))
            if bare != norm(d.name):
                self._add(bare, loc)
        for alias, (sraw, draw) in DISTRICT_ALIASES.items():
            d = next((x for x in store.districts if x.state_raw == sraw and x.name_raw == draw), None)
            if d:
                self._add(alias, Location("district", d.state, d.name), allow_short=True, override=True)
        self._add("india", Location("country"), allow_short=True, override=True)

        # states win over same-named districts (e.g. Delhi, Puducherry, Chandigarh)
        for key, locs in self.keys.items():
            states = [l for l in locs if l.kind != "district"]
            if states:
                self.keys[key] = states[:1]
        for key, locs in self.keys.items():
            if len(locs) > 1:
                for l in locs:
                    l.also_in = [o.state for o in locs if o is not l]
        self._key_list = list(self.keys)

    def _add(self, key: str, loc: Location, allow_short: bool = False, override: bool = False):
        if not key or key in STOP_KEYS or (len(key) < 4 and not allow_short):
            return
        if override or key not in self.keys:
            self.keys[key] = [loc]
        elif all((l.state, l.district) != (loc.state, loc.district) for l in self.keys[key]):
            self.keys[key].append(loc)

    # ------------------------------------------------------------------
    def _pick(self, locs: List[Location], hint_states: List[str]) -> Location:
        for l in locs:
            if l.state in hint_states:
                return l
        return locs[0]

    def find_all(self, text: str, hint_state: Optional[str] = None, fuzzy: bool = True) -> List[Location]:
        """Locations mentioned in free text, in order, without duplicates."""
        tokens = norm(text).split()
        found: List[Tuple[str, List[Location]]] = []
        i = 0
        while i < len(tokens):
            for n in (4, 3, 2, 1):
                key = " ".join(tokens[i:i + n])
                if key in self.keys:
                    found.append((key, self.keys[key]))
                    i += n
                    break
            else:
                i += 1
        if not found and fuzzy:
            found = self._fuzzy_scan(tokens)
        hints = [l.state for _, locs in found for l in locs if l.kind == "state"]
        if hint_state:
            hints.append(hint_state)
        out: List[Location] = []
        for _, locs in found:
            loc = self._pick(locs, hints)
            if all((o.kind, o.state, o.district) != (loc.kind, loc.state, loc.district) for o in out):
                out.append(loc)
        return out

    def _fuzzy_scan(self, tokens: List[str]):
        found = []
        for n in (3, 2, 1):
            for i in range(len(tokens) - n + 1):
                chunk = tokens[i:i + n]
                if any(t in QUERY_WORDS for t in chunk):
                    continue
                key = " ".join(chunk)
                if len(key) < 5:
                    continue
                m = difflib.get_close_matches(key, self._key_list, n=1, cutoff=0.86)
                if m:
                    found.append((m[0], self.keys[m[0]]))
            if found:
                break
        return found

    def resolve(self, name: str, hint_state: Optional[str] = None) -> Optional[Location]:
        """Resolve one name coming from the LLM (more lenient than free text)."""
        key = norm(name)
        if not key:
            return None
        hints = [hint_state] if hint_state else []
        if key in self.keys:
            return self._pick(self.keys[key], hints)
        hits = self.find_all(name, hint_state, fuzzy=False)
        if hits:
            return hits[0]
        m = difflib.get_close_matches(key, self._key_list, n=1, cutoff=0.74)
        return self._pick(self.keys[m[0]], hints) if m else None
