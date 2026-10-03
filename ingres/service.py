"""Application logic: chat engine + read-only data queries.

Framework free on purpose so it can be unit-tested without FastAPI.
"""
from __future__ import annotations

import difflib
from typing import Dict, List, Optional

from .data import (CATEGORY_COLORS, CATEGORY_LABELS, CATEGORY_ORDER, METRICS, Store,
                   get_store)
from .geo import map_tiles
from .locations import Location, LocationIndex
from .nlu import LANGUAGES, detect_language, rule_parse


class NotFound(Exception):
    pass


# ------------------------------------------------------------------ helpers
def fmt(value: Optional[float], digits: int = 1) -> str:
    return "n/a" if value is None else f"{value:,.{digits}f}"


def stage_text(stage: Optional[float], category: str) -> str:
    return "n/a" if stage is None else f"{fmt(stage)}% ({CATEGORY_LABELS[category]})"


def with_unit(value: Optional[float], digits: int, unit: str) -> str:
    return fmt(value, digits) + ("" if unit == "%" else " ") + unit


def counts_text(counts: Dict[str, int]) -> str:
    parts = [f"{counts[c]} {CATEGORY_LABELS[c]}" for c in CATEGORY_ORDER if counts.get(c)]
    return ", ".join(parts) if parts else "no data"


def agg_row(name: str, subtitle: str, agg: dict) -> dict:
    cat = agg["category"]
    return {
        "name": name, "subtitle": subtitle, "rainfall": agg["avg_rainfall"],
        "extraction_stage": agg["stage"], "gw_recharge": agg["total_recharge"],
        "net_availability": agg["total_net"], "category": cat,
        "category_label": CATEGORY_LABELS[cat],
    }


def metric_sentence(vals: dict, primary: str) -> str:
    """vals: rainfall, stage, category, recharge, net -> one sentence, primary metric first."""
    pieces = {
        "rainfall": f"average rainfall {fmt(vals['rainfall'])} mm",
        "extraction": f"stage of groundwater extraction {stage_text(vals['stage'], vals['category'])}",
        "recharge": f"annual recharge {fmt(vals['recharge'], 0)} ham",
        "availability": f"net availability for future use {fmt(vals['net'], 0)} ham",
    }
    order = [primary] + [m for m in pieces if m != primary] if primary in pieces else list(pieces)
    return "; ".join(pieces[m] for m in order)


def _vals_from_agg(agg: dict) -> dict:
    return {"rainfall": agg["avg_rainfall"], "stage": agg["stage"], "category": agg["category"],
            "recharge": agg["total_recharge"], "net": agg["total_net"]}


def _vals_from_district(d) -> dict:
    return {"rainfall": d.rainfall, "stage": d.stage, "category": d.category,
            "recharge": d.recharge, "net": d.net}


def _bar_color(cat: str) -> str:
    return CATEGORY_COLORS[cat]


class ChatService:
    def __init__(self, store: Optional[Store] = None, llm=None):
        self.store = store or get_store()
        self.index = LocationIndex(self.store)
        self.llm = llm

    # ================================================================ read API
    def state_name(self, name: str) -> str:
        loc = self.index.resolve(name)
        if not loc or loc.kind != "state":
            raise NotFound(f"State not found: {name}")
        return loc.state  # type: ignore[return-value]

    def states(self) -> List[str]:
        return list(self.store.states)

    def districts(self, state: str) -> List[str]:
        return sorted(d.name for d in self.store.districts_of(self.state_name(state)))

    def state_data(self, state: str) -> List[dict]:
        return [d.row() for d in self.store.districts_of(self.state_name(state))]

    def state_stats(self, state: str) -> dict:
        s = self.state_name(state)
        return {"state": s, **self.store.state_summary(s)}

    def total_stats(self) -> dict:
        return {
            "total_records": len(self.store.districts),
            "total_states": len(self.store.states),
            "total_districts": len({(d.state, d.name) for d in self.store.districts}),
            "india": self.store.india_summary(),
            "gemini_enabled": bool(self.llm and self.llm.configured),
        }

    def map_data(self) -> dict:
        return {"tiles": map_tiles(self.store), "legend": [
            {"key": c, "label": CATEGORY_LABELS[c], "color": CATEGORY_COLORS[c]} for c in CATEGORY_ORDER]}

    def rankings(self, metric: str = "extraction", order: str = "desc", limit: int = 10,
                 state: Optional[str] = None, level: str = "district") -> dict:
        if metric not in METRICS:
            raise ValueError(f"metric must be one of {sorted(METRICS)}")
        limit = max(1, min(50, limit))
        if level == "state":
            total, items = self.store.rank_states(metric, order, limit)
            field = METRICS[metric][1]
            return {"level": "state", "metric": metric, "total": total,
                    "items": [{"name": s, "value": a[field], "category": a["category"]} for s, a in items]}
        st = self.state_name(state) if state else None
        total, items = self.store.rank_districts(metric, order, limit, st)
        field = METRICS[metric][0]
        return {"level": "district", "metric": metric, "total": total,
                "items": [{"name": d.name, "state": d.state, "value": getattr(d, field),
                           "category": d.category} for d in items]}

    def health(self) -> dict:
        return {
            "status": "healthy", "rows": len(self.store.districts), "states": len(self.store.states),
            "gemini_configured": bool(self.llm and self.llm.configured),
            "gemini_available": bool(self.llm and self.llm.available),
            "gemini_last_error": getattr(self.llm, "last_error", None),
            "gemini_models": getattr(self.llm, "models", []),
        }

    # ================================================================ chat
    async def chat(self, message: str, language: str = "auto", context: Optional[dict] = None) -> dict:
        ctx = context or {}
        hint_state = ctx.get("state")
        nlu = None
        source = "rules"
        llm_failed = False
        if self.llm and self.llm.available:
            try:
                nlu = await self.llm.parse(message, ctx)
                source = "gemini"
            except Exception:
                llm_failed = True
        elif self.llm and self.llm.configured:
            llm_failed = True            # key present but cooling down
        if nlu is None:
            nlu = rule_parse(message, self.index, hint_state)
        else:                            # let the rules rescue weak model output
            rules = rule_parse(message, self.index, hint_state)
            if nlu["intent"] == "unknown" and rules["intent"] != "unknown":
                rules["language"] = nlu["language"]
                nlu = rules
            elif nlu["intent"] in ("lookup", "compare") and not nlu["locations"] and rules["locations"]:
                nlu["locations"] = rules["locations"]

        lang = language if language in LANGUAGES else nlu["language"]
        answer = self._route(nlu, ctx)

        notice = None
        if lang != "en":
            if self.llm and self.llm.available and not llm_failed:
                try:
                    answer["text"] = await self.llm.localize(answer["text"], lang)
                except Exception:
                    notice = "Translation is temporarily unavailable, so this answer is shown in English."
            elif self.llm and self.llm.configured:
                notice = "Translation is temporarily unavailable, so this answer is shown in English."
            else:
                notice = "Add a GEMINI_API_KEY to receive answers in your language. Showing English."
        return {
            "response": answer["text"], "data": answer.get("data") or None,
            "charts": answer.get("charts") or None, "suggestions": answer.get("suggestions") or None,
            "language": lang, "source": source, "notice": notice,
            "context": answer.get("context") or ctx or None,
        }

    # ------------------------------------------------------------ routing
    def _resolve(self, names: List[str], ctx: dict) -> List[Location]:
        first = [self.index.resolve(n) for n in names]
        hints = [l.state for l in first if l and l.kind == "state"]
        hint = hints[0] if hints else ctx.get("state")
        locs: List[Location] = []
        for name, loc in zip(names, first):
            if loc and loc.also_in:
                loc = self.index.resolve(name, hint) or loc
            if loc and all((o.kind, o.state, o.district) != (loc.kind, loc.state, loc.district) for o in locs):
                locs.append(loc)
        # "Aurangabad Maharashtra" -> keep the district, drop the redundant state
        dist_states = {l.state for l in locs if l.kind == "district"}
        if len(locs) > 1:
            locs = [l for l in locs if not (l.kind == "state" and l.state in dist_states)] or locs
        return locs

    def _route(self, nlu: dict, ctx: dict) -> dict:
        intent, metric = nlu["intent"], nlu["metric"]
        if intent == "greet":
            return self._greet()
        if intent == "help":
            return self._help()
        if intent == "list_states":
            return self._list_states()

        names = nlu["locations"]
        locs = self._resolve(names, ctx)
        missing = [n for n in names if not self.index.resolve(n)]

        if intent == "compare":
            if len(locs) < 2:
                return self._need_two(missing)
            return self._compare(locs[:4], metric)
        if intent in ("ranking", "categories"):
            return self._ranking(nlu, locs) if intent == "ranking" else self._categories(nlu, locs)
        if intent == "lookup" or locs:
            if not locs and ctx and (ctx.get("district") or ctx.get("state")):
                loc = (Location("district", ctx.get("state"), ctx["district"]) if ctx.get("district")
                       else Location("state", ctx["state"]))
                locs = [loc]
            if not locs and not missing and metric != "overview":
                locs = self._resolve(["India"], ctx)     # "recharge" alone -> all-India figure
            if not locs:
                return self._not_found(missing) if missing else self._ask_place()
            return self._lookup(locs[0], metric)
        return self._unknown(missing)

    # ------------------------------------------------------------ handlers
    def _suggest_starters(self) -> List[str]:
        return ["Rainfall in Bengaluru", "Most over-exploited districts in Punjab",
                "Compare Karnataka and Kerala", "Top 5 states by groundwater extraction"]

    def _greet(self) -> dict:
        s = self.store
        return {"text": (f"Hello! I'm the INGRES groundwater assistant. I can answer questions about rainfall, "
                         f"recharge, extraction and water availability for {len(s.states)} states and UTs "
                         f"({len(s.districts)} assessment units, CGWB 2024-25). What would you like to know?"),
                "suggestions": self._suggest_starters()}

    def _help(self) -> dict:
        return {"text": ("You can ask me to:\n"
                         "• look up a state or district — “groundwater in Pune”\n"
                         "• compare places — “Compare Punjab and Kerala”\n"
                         "• rank them — “Top 5 over-exploited districts in Rajasthan”\n"
                         "• count safety categories — “How many districts are critical in Gujarat?”\n"
                         "I understand English, Hindi, Kannada, Telugu, Tamil, Marathi, Bengali and Gujarati."),
                "suggestions": self._suggest_starters()}

    def _map_chart(self, title: str, metric: str = "stage", highlight: Optional[List[str]] = None) -> dict:
        return {"type": "map", "title": title, "metric": metric,
                "data": map_tiles(self.store), "highlight": highlight or []}

    def _list_states(self) -> dict:
        s = self.store
        sample = [x for x in ("Punjab", "Rajasthan", "Kerala", "Karnataka", "Uttar Pradesh") if x in s.states]
        return {"text": (f"I have data for {len(s.states)} states and union territories covering "
                         f"{len(s.districts)} districts. Tap a tile on the map or name any of them."),
                "charts": [self._map_chart("Groundwater extraction category by state")],
                "suggestions": sample}

    def _lookup(self, loc: Location, metric: str) -> dict:
        if loc.kind == "country":
            agg = self.store.india_summary()
            text = (f"India overall (2024-25): {metric_sentence(_vals_from_agg(agg), metric)}. "
                    f"Of {agg['n_districts']} assessment units: {counts_text(agg['counts'])}.")
            return {"text": text, "charts": [self._map_chart("Groundwater extraction category by state"),
                                             self._categories_chart("India", agg["counts"])],
                    "suggestions": ["Top 5 states by groundwater extraction", "Most over-exploited districts in India",
                                    "Lowest rainfall states"], "context": {}}
        if loc.kind == "district":
            d = self.store.find_district(loc.state, loc.district)
            if d is None:
                raise NotFound(loc.label)
            text = f"{d.name} ({d.state}): {metric_sentence(_vals_from_district(d), metric)}."
            if loc.also_in:
                text += f" Note: another district with this name exists in {', '.join(loc.also_in)}."
            others = [x for x in self.store.districts_of(d.state) if x.name != d.name]
            others.sort(key=lambda x: x.stage if x.stage is not None else -1, reverse=True)
            sugg = [f"Compare {d.name} and {others[0].name}"] if others else []
            sugg += [f"Overview of {d.state}", f"Most over-exploited districts in {d.state}"]
            return {"text": text, "data": [d.row()], "suggestions": sugg,
                    "context": {"state": d.state, "district": d.name}}
        agg = self.store.state_summary(loc.state)
        if agg is None:
            raise NotFound(loc.label)
        text = (f"{loc.state}: {metric_sentence(_vals_from_agg(agg), metric)}. "
                f"Across {agg['n_districts']} districts: {counts_text(agg['counts'])}.")
        field = {"rainfall": "rainfall", "recharge": "recharge", "availability": "net"}.get(metric, "stage")
        _, top = self.store.rank_districts({"stage": "extraction", "net": "availability"}.get(field, field), "desc", 8, loc.state)
        label, unit = {"rainfall": ("Rainfall", "mm"), "recharge": ("Annual recharge", "ham"),
                       "availability": ("Net availability", "ham")}.get(metric, ("Stage of extraction", "%"))
        bars = {"type": "bar", "title": f"{label} — top districts in {loc.state}", "unit": unit,
                "data": [{"name": d.name, "value": round(getattr(d, field), 1), "color": _bar_color(d.category)} for d in top]}
        charts = [self._categories_chart(loc.state, agg["counts"]), bars]
        _, worst = self.store.rank_districts("extraction", "desc", 4, loc.state)
        sugg = [f"Most over-exploited districts in {loc.state}", f"Driest districts in {loc.state}"]
        if worst:
            sugg.append(worst[0].name)
        return {"text": text, "charts": charts, "data": [d.row() for d in worst[:4]],
                "suggestions": sugg, "context": {"state": loc.state}}

    def _categories_chart(self, scope: str, counts: Dict[str, int]) -> dict:
        return {"type": "categories", "title": f"Safety categories — {scope}",
                "data": [{"name": CATEGORY_LABELS[c], "value": counts[c], "color": CATEGORY_COLORS[c]}
                         for c in CATEGORY_ORDER if counts.get(c)]}

    def _entity(self, loc: Location) -> Optional[dict]:
        if loc.kind == "district":
            d = self.store.find_district(loc.state, loc.district)
            return None if d is None else {"name": d.name, "row": d.row(), "vals": _vals_from_district(d)}
        if loc.kind == "state":
            agg = self.store.state_summary(loc.state)
            return None if agg is None else {"name": loc.state, "row": agg_row(loc.state, "State / UT", agg),
                                             "vals": _vals_from_agg(agg)}
        agg = self.store.india_summary()
        return {"name": "India", "row": agg_row("India", "All India", agg), "vals": _vals_from_agg(agg)}

    def _compare(self, locs: List[Location], metric: str) -> dict:
        ents = [e for e in (self._entity(l) for l in locs) if e]
        if len(ents) < 2:
            return self._need_two([])
        names = " vs ".join(e["name"] for e in ents)
        lines = []
        order = [metric] + [m for m in ("extraction", "rainfall", "recharge", "availability") if m != metric] \
            if metric in METRICS else ["extraction", "rainfall", "availability"]
        for m in order[:3]:
            key = {"extraction": "stage", "availability": "net"}.get(m, m)
            label = {"extraction": "Stage of extraction", "rainfall": "Average rainfall (mm)",
                     "recharge": "Annual recharge (ham)", "availability": "Net availability (ham)"}[m]
            parts = []
            for e in ents:
                v = e["vals"][key]
                parts.append(f"{e['name']} {stage_text(v, e['vals']['category']) if m == 'extraction' else fmt(v, 1 if m == 'rainfall' else 0)}")
            lines.append(f"{label}: " + ", ".join(parts))
        rated = [e for e in ents if e["vals"]["stage"] is not None]
        if rated:
            top = max(rated, key=lambda e: e["vals"]["stage"])
            lines.append(f"Highest extraction pressure: {top['name']}.")
        chart = {"type": "comparison", "title": "Rainfall (mm) vs extraction stage (%)",
                 "data": [{"name": e["name"], "rainfall": e["vals"]["rainfall"], "extraction": e["vals"]["stage"],
                           "color": _bar_color(e["vals"]["category"])} for e in ents]}
        first = locs[0]
        return {"text": f"{names}\n" + "\n".join(lines), "data": [e["row"] for e in ents], "charts": [chart],
                "suggestions": [f"Overview of {ents[0]['name']}", f"Overview of {ents[1]['name']}"],
                "context": {"state": first.state, **({"district": first.district} if first.district else {})} if first.kind != "country" else {}}

    def _ranking(self, nlu: dict, locs: List[Location]) -> dict:
        metric = nlu["metric"] if nlu["metric"] in METRICS else "extraction"
        order, limit, cat = nlu["order"], nlu["limit"], nlu["category"]
        scope = next((l.state for l in locs if l.kind in ("state", "district") and l.state), None)
        label, unit = METRICS[metric][2], METRICS[metric][3]
        direction = "highest" if order == "desc" else "lowest"

        if nlu["level"] == "state" and not scope and not cat:
            total, items = self.store.rank_states(metric, order, limit)
            field = METRICS[metric][1]
            rows = [f"{i}. {s} — {with_unit(a[field], 1 if unit in ('mm', '%') else 0, unit)}" for i, (s, a) in enumerate(items, 1)]
            bars = {"type": "bar", "title": f"States by {label} ({direction} first)", "unit": unit,
                    "data": [{"name": s, "value": round(a[field], 1), "color": _bar_color(a["category"])} for s, a in items]}
            charts = [bars, self._map_chart(f"States — {label}", "rainfall" if metric == "rainfall" else "stage",
                                            [s for s, _ in items])]
            return {"text": f"Top {len(items)} states by {label} ({direction} first):\n" + "\n".join(rows),
                    "charts": charts, "suggestions": [f"Overview of {items[0][0]}"] if items else [],
                    "context": {}}

        total, items = self.store.rank_districts(metric, order, limit, scope, cat)
        where = f"in {scope}" if scope else "in India"
        if not items:
            what = CATEGORY_LABELS[cat] if cat else label
            return {"text": f"No districts {where} match “{what}”.", "suggestions": self._suggest_starters()}
        field = METRICS[metric][0]
        rows = [f"{i}. {d.name}{'' if scope else ', ' + d.state} — {with_unit(getattr(d, field), 1 if unit in ('mm', '%') else 0, unit)} ({CATEGORY_LABELS[d.category]})"
                for i, d in enumerate(items, 1)]
        if cat:
            head = f"{total} districts {where} are {CATEGORY_LABELS[cat]}. Showing {len(items)} with the {direction} {label}:"
        else:
            head = f"Top {len(items)} districts {where} by {label} ({direction} first):"
        bars = {"type": "bar", "title": f"Districts {where} — {label}", "unit": unit,
                "data": [{"name": d.name, "value": round(getattr(d, field), 1), "color": _bar_color(d.category)} for d in items]}
        return {"text": head + "\n" + "\n".join(rows), "charts": [bars], "data": [d.row() for d in items[:4]],
                "suggestions": [f"Overview of {items[0].state}", f"Compare {items[0].name} and {items[1].name}"] if len(items) > 1 else [f"Overview of {items[0].state}"],
                "context": {"state": items[0].state} if scope else {}}

    def _categories(self, nlu: dict, locs: List[Location]) -> dict:
        scope = next((l.state for l in locs if l.state), None)
        if scope:
            agg = self.store.state_summary(scope)
            name = scope
        else:
            agg, name = self.store.india_summary(), "India"
        cat = nlu["category"]
        if cat:
            n = agg["counts"][cat]
            text = f"{name}: {n} of {agg['n_districts']} districts are {CATEGORY_LABELS[cat]}. Breakdown: {counts_text(agg['counts'])}."
        else:
            text = f"{name}: {counts_text(agg['counts'])} (out of {agg['n_districts']} districts)."
        return {"text": text, "charts": [self._categories_chart(name, agg["counts"])],
                "suggestions": [f"Most over-exploited districts in {name}" if scope else "Most over-exploited districts in India"],
                "context": {"state": scope} if scope else {}}

    # ------------------------------------------------------------ fallbacks
    def _need_two(self, missing: List[str]) -> dict:
        extra = f" I couldn't find: {', '.join(missing)}." if missing else ""
        return {"text": "Please name at least two places to compare, for example “Compare Karnataka and Kerala”." + extra,
                "suggestions": ["Compare Punjab and Haryana", "Compare Pune and Nagpur"]}

    def _ask_place(self) -> dict:
        return {"text": "Which state or district do you mean? For example “rainfall in Pune” or “Karnataka”.",
                "suggestions": ["Karnataka", "Rainfall in Pune", "India overview"]}

    def _not_found(self, missing: List[str]) -> dict:
        name = missing[0]
        close = difflib.get_close_matches(name.lower(), self.index._key_list, n=3, cutoff=0.5)
        hint = f" Did you mean {', '.join(c.title() for c in close)}?" if close else ""
        return {"text": f"I couldn't find “{name}” in the dataset.{hint}", "suggestions": [c.title() for c in close] or ["Show all states"]}

    def _unknown(self, missing: List[str]) -> dict:
        if missing:
            return self._not_found(missing)
        return {"text": ("Sorry, I didn't understand that. I can look up a state or district (“rainfall in Pune”), "
                         "compare places, or rank them (“top 5 over-exploited districts”)."),
                "suggestions": self._suggest_starters()}
