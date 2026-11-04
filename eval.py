"""Small evaluation: does the detector find the planted problems, and how many false alarms?

Run: python eval.py
Also checks that numeric answers match a direct pandas calculation.
"""
from linecopilot.datagen import GROUND_TRUTH, generate
from linecopilot.tools import Plant

plant = Plant(generate())
found = {(a["line"], a["shift"], a["day"]) for a in plant.detect_anomalies()["anomalies"]}

truth = set()
for d in GROUND_TRUTH["crimp_drift"]["days"]:
    for s in ["Day", "Swing", "Night"]:
        truth.add(("Line 2", s, d))
for d in range(GROUND_TRUTH["vision_lighting"]["start_day"], 15):
    truth.add(("Line 3", "Night", d))

tp, fp, fn = len(found & truth), len(found - truth), len(truth - found)
precision, recall = tp / (tp + fp), tp / (tp + fn)
print(f"planted cells: {len(truth)} | flagged: {len(found)}")
print(f"true positives {tp}, false positives {fp}, missed {fn}")
print(f"precision {precision:.2f}, recall {recall:.2f}")
for f in sorted(found - truth):
    print("false positive:", f)

# numeric spot check against raw pandas
df = plant.df
l3 = df[(df.line == "Line 3") & (df["shift"] == "Night")]
k = plant.kpi_summary(line="Line 3", shift="Night")
assert k["defects"] == int(l3.defects.sum()) and k["units"] == int(l3.units.sum())
print("KPI spot check passed")
