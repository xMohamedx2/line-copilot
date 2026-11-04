"""Synthetic production data for a fictional connector assembly area.

All data is made up. Two root causes are planted on purpose so the agent can be
checked against ground truth:

  1. Line 2, crimp height drifts out of spec on days 8-10 (defect type: crimp_height)
  2. Line 3, night shift, vision lighting degrades from day 11 on (defect type: vision_false_reject)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LINES = ["Line 1", "Line 2", "Line 3"]
SHIFTS = {"Day": range(6, 14), "Swing": range(14, 22), "Night": list(range(22, 24)) + list(range(0, 6))}
DEFECT_TYPES = ["crimp_height", "terminal_bend", "housing_crack", "missing_terminal", "vision_false_reject"]
DOWNTIME_REASONS = ["changeover", "feeder_jam", "vision_fault", "material_wait", "operator_break", "none"]

GROUND_TRUTH = {
    "crimp_drift": {"line": "Line 2", "days": [8, 9, 10], "defect_type": "crimp_height"},
    "vision_lighting": {"line": "Line 3", "shift": "Night", "start_day": 11, "defect_type": "vision_false_reject"},
}


def _shift_of(hour: int) -> str:
    for name, hours in SHIFTS.items():
        if hour in hours:
            return name
    raise ValueError(hour)


def generate(days: int = 14, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2026-10-12 00:00")
    rows = []
    for d in range(1, days + 1):
        for h in range(24):
            ts = start + pd.Timedelta(days=d - 1, hours=h)
            shift = _shift_of(h)
            for line in LINES:
                units = int(rng.normal(1200, 60))
                base_rate = 0.008
                rates = {t: base_rate / len(DEFECT_TYPES) for t in DEFECT_TYPES}

                if line == "Line 2" and d in GROUND_TRUTH["crimp_drift"]["days"]:
                    rates["crimp_height"] += 0.025
                if line == "Line 3" and shift == "Night" and d >= GROUND_TRUTH["vision_lighting"]["start_day"]:
                    rates["vision_false_reject"] += 0.03

                defect_counts = {t: int(rng.binomial(units, r)) for t, r in rates.items()}
                defects = sum(defect_counts.values())
                top_defect = max(defect_counts, key=defect_counts.get) if defects else "none"

                dt_min, reason = 0.0, "none"
                if rng.random() < 0.18:
                    reason = rng.choice(DOWNTIME_REASONS[:-1], p=[0.25, 0.30, 0.15, 0.20, 0.10])
                    dt_min = float(np.clip(rng.gamma(2.0, 4.0), 1, 45))
                if line == "Line 3" and shift == "Night" and d >= 11 and rng.random() < 0.25:
                    reason, dt_min = "vision_fault", float(np.clip(rng.gamma(3.0, 5.0), 5, 55))
                units = int(units * (1 - dt_min / 60))

                rows.append(
                    dict(
                        timestamp=ts, day=d, hour=h, shift=shift, line=line, units=units,
                        defects=defects, top_defect=top_defect,
                        **{f"d_{t}": c for t, c in defect_counts.items()},
                        downtime_min=round(dt_min, 1), downtime_reason=reason,
                    )
                )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import pathlib

    out = pathlib.Path(__file__).resolve().parent.parent / "data" / "production.csv"
    df = generate()
    df.to_csv(out, index=False)
    print(f"wrote {len(df)} rows to {out}")
