"""Analytics and retrieval tools the agent can call.

Every tool returns plain dicts so results can be handed straight to an LLM
and also checked in unit tests.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Plant:
    def __init__(self, df: pd.DataFrame | None = None, sop_dir: pathlib.Path | None = None):
        if df is None:
            df = pd.read_csv(ROOT / "data" / "production.csv", parse_dates=["timestamp"])
        self.df = df
        sop_dir = sop_dir or ROOT / "data" / "sops"
        self.sops = {p.name: p.read_text() for p in sorted(sop_dir.glob("*.md"))}
        self._vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self._mat = self._vec.fit_transform([t.replace("_", " ") for t in self.sops.values()])

    # ---- helpers -------------------------------------------------------
    def _filter(self, line=None, shift=None, day_from=None, day_to=None) -> pd.DataFrame:
        d = self.df
        if line:
            d = d[d.line == line]
        if shift:
            d = d[d["shift"] == shift]
        if day_from is not None:
            d = d[d.day >= day_from]
        if day_to is not None:
            d = d[d.day <= day_to]
        return d

    # ---- tools ---------------------------------------------------------
    def kpi_summary(self, line=None, shift=None, day_from=None, day_to=None) -> dict:
        d = self._filter(line, shift, day_from, day_to)
        if d.empty:
            return {"error": "no rows match the filter"}
        units, defects = int(d.units.sum()), int(d.defects.sum())
        return {
            "filter": {"line": line, "shift": shift, "day_from": day_from, "day_to": day_to},
            "units": units,
            "defects": defects,
            "defect_rate_pct": round(100 * defects / units, 3),
            "downtime_min": round(float(d.downtime_min.sum()), 1),
            "downtime_events": int((d.downtime_min > 0).sum()),
        }

    def top_downtime(self, line=None, shift=None, day_from=None, day_to=None, n=3) -> dict:
        d = self._filter(line, shift, day_from, day_to)
        d = d[d.downtime_reason != "none"]
        g = d.groupby("downtime_reason").downtime_min.agg(["sum", "count"]).sort_values("sum", ascending=False).head(n)
        return {
            "filter": {"line": line, "shift": shift, "day_from": day_from, "day_to": day_to},
            "top_reasons": [
                {"reason": r, "minutes": round(float(row["sum"]), 1), "events": int(row["count"])}
                for r, row in g.iterrows()
            ],
        }

    def defect_pareto(self, line=None, shift=None, day_from=None, day_to=None) -> dict:
        d = self._filter(line, shift, day_from, day_to)
        cols = [c for c in d.columns if c.startswith("d_")]
        g = d[cols].sum().rename(lambda c: c[2:]).sort_values(ascending=False)
        g = g[g > 0]
        total = max(int(g.sum()), 1)
        return {
            "filter": {"line": line, "shift": shift, "day_from": day_from, "day_to": day_to},
            "pareto": [{"defect": k, "count": int(v), "pct": round(100 * v / total, 1)} for k, v in g.items()],
        }

    def detect_anomalies(self, z_threshold: float = 3.0) -> dict:
        """Flag line/shift/day cells whose defect rate is far above that line/shift's own baseline.

        Uses a robust z-score (median and MAD) so the anomalies themselves do not
        inflate the baseline.
        """
        g = self.df.groupby(["line", "shift", "day"]).agg(units=("units", "sum"), defects=("defects", "sum")).reset_index()
        g["rate"] = g.defects / g.units
        out = []
        for (line, shift), grp in g.groupby(["line", "shift"]):
            med = grp.rate.median()
            mad = (grp.rate - med).abs().median() or 1e-9
            grp = grp.assign(z=0.6745 * (grp.rate - med) / mad)
            for _, r in grp[grp.z > z_threshold].iterrows():
                d = self.df[(self.df.line == line) & (self.df["shift"] == shift) & (self.df.day == r.day)]
                dp = self.defect_pareto(line, shift, int(r.day), int(r.day))["pareto"]
                out.append(
                    {
                        "line": line, "shift": shift, "day": int(r.day),
                        "defect_rate_pct": round(float(100 * r.rate), 2),
                        "baseline_pct": round(float(100 * med), 2),
                        "robust_z": round(float(r.z), 1),
                        "main_defect": dp[0]["defect"] if dp else None,
                        "downtime_min": round(float(d.downtime_min.sum()), 1),
                    }
                )
        out.sort(key=lambda x: -x["robust_z"])
        return {"z_threshold": z_threshold, "anomalies": out}

    def incidents(self, z_threshold: float = 3.0) -> dict:
        """Group anomalous line/shift/day cells into incidents by line and main defect."""
        groups: dict = {}
        for a in self.detect_anomalies(z_threshold)["anomalies"]:
            g = groups.setdefault((a["line"], a["main_defect"]), {"cells": []})
            g["cells"].append(a)
        out = []
        for (line, defect), g in groups.items():
            c = g["cells"]
            out.append({
                "line": line, "main_defect": defect,
                "shifts": sorted({x["shift"] for x in c}),
                "first_day": min(x["day"] for x in c), "last_day": max(x["day"] for x in c),
                "peak_defect_rate_pct": max(x["defect_rate_pct"] for x in c),
                "baseline_pct": c[0]["baseline_pct"],
                "downtime_min": round(sum(x["downtime_min"] for x in c), 1),
                "cells_flagged": len(c),
            })
        out.sort(key=lambda x: -x["peak_defect_rate_pct"])
        return {"incidents": out}

    def compare_shifts(self, line=None, day_from=None, day_to=None) -> dict:
        res = {}
        for s in ["Day", "Swing", "Night"]:
            res[s] = self.kpi_summary(line, s, day_from, day_to)
        return {"line": line, "by_shift": res}

    def search_sops(self, query: str, k: int = 2) -> dict:
        q = self._vec.transform([query.replace("_", " ")])
        sims = cosine_similarity(q, self._mat).ravel()
        idx = np.argsort(-sims)[:k]
        names = list(self.sops)
        return {
            "query": query,
            "results": [
                {"doc": names[i], "score": round(float(sims[i]), 3), "text": self.sops[names[i]]}
                for i in idx
                if sims[i] > 0
            ],
        }


# JSON schemas in Anthropic tool-use format
TOOL_SPECS = [
    {
        "name": "kpi_summary",
        "description": "Units, defects, defect rate, and downtime for an optional line/shift/day range. Days are 1-14.",
        "input_schema": {"type": "object", "properties": {
            "line": {"type": "string", "enum": ["Line 1", "Line 2", "Line 3"]},
            "shift": {"type": "string", "enum": ["Day", "Swing", "Night"]},
            "day_from": {"type": "integer"}, "day_to": {"type": "integer"}}},
    },
    {
        "name": "top_downtime",
        "description": "Top downtime reasons by minutes for an optional filter.",
        "input_schema": {"type": "object", "properties": {
            "line": {"type": "string"}, "shift": {"type": "string"},
            "day_from": {"type": "integer"}, "day_to": {"type": "integer"}, "n": {"type": "integer"}}},
    },
    {
        "name": "defect_pareto",
        "description": "Defect types ranked by count with percentages for an optional filter.",
        "input_schema": {"type": "object", "properties": {
            "line": {"type": "string"}, "shift": {"type": "string"},
            "day_from": {"type": "integer"}, "day_to": {"type": "integer"}}},
    },
    {
        "name": "detect_anomalies",
        "description": "Find line/shift/day combinations with defect rates far above their own baseline.",
        "input_schema": {"type": "object", "properties": {"z_threshold": {"type": "number"}}},
    },
    {
        "name": "incidents",
        "description": "Grouped summary of problems: anomalous cells rolled up by line and main defect, with shifts, day range and peak rate. Best first call for 'what is wrong'.",
        "input_schema": {"type": "object", "properties": {"z_threshold": {"type": "number"}}},
    },
    {
        "name": "compare_shifts",
        "description": "KPI comparison across Day, Swing and Night shifts, optionally for one line.",
        "input_schema": {"type": "object", "properties": {
            "line": {"type": "string"}, "day_from": {"type": "integer"}, "day_to": {"type": "integer"}}},
    },
    {
        "name": "search_sops",
        "description": "Search the standard operating procedures for troubleshooting steps. Use after finding a problem.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}}, "required": ["query"]},
    },
]
