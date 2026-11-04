import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pytest

from linecopilot.agent import ask_offline, _parse_filters
from linecopilot.datagen import GROUND_TRUTH, generate
from linecopilot.tools import Plant


@pytest.fixture(scope="module")
def plant():
    return Plant(generate())


def test_kpi_totals_match_raw(plant):
    k = plant.kpi_summary()
    assert k["units"] == int(plant.df.units.sum())
    assert k["defects"] == int(plant.df.defects.sum())
    assert k["defect_rate_pct"] == pytest.approx(100 * k["defects"] / k["units"], abs=1e-3)


def test_filter_line_shift_day(plant):
    k = plant.kpi_summary(line="Line 2", shift="Night", day_from=9, day_to=9)
    assert k["units"] == int(plant.df[(plant.df.line == "Line 2") & (plant.df["shift"] == "Night") & (plant.df.day == 9)].units.sum())


def test_empty_filter_returns_error(plant):
    assert "error" in plant.kpi_summary(line="Line 9")


def test_pareto_sums_to_100(plant):
    p = plant.defect_pareto()["pareto"]
    assert sum(x["pct"] for x in p) == pytest.approx(100, abs=0.5)


def test_planted_crimp_drift_found(plant):
    found = {(a["line"], a["day"]) for a in plant.detect_anomalies()["anomalies"] if a["main_defect"] == "crimp_height"}
    for d in GROUND_TRUTH["crimp_drift"]["days"]:
        assert ("Line 2", d) in found


def test_planted_vision_issue_found(plant):
    found = {(a["line"], a["shift"], a["day"]) for a in plant.detect_anomalies()["anomalies"]}
    for d in range(GROUND_TRUTH["vision_lighting"]["start_day"], 15):
        assert ("Line 3", "Night", d) in found


def test_sop_search_routes_correctly(plant):
    assert plant.search_sops("vision false rejects lighting")["results"][0]["doc"] == "vision_false_rejects.md"
    assert plant.search_sops("crimp height tooling")["results"][0]["doc"] == "crimp_height_out_of_spec.md"


def test_parse_filters():
    assert _parse_filters("Line 3 night shift days 8-10") == {"line": "Line 3", "shift": "Night", "day_from": 8, "day_to": 10}
    assert _parse_filters("what happened on day 5")["day_from"] == 5
    assert "shift" not in _parse_filters("day 5 summary")


def test_offline_agent_uses_tools_and_cites(plant):
    r = ask_offline(plant, "What looks wrong in the data?")
    assert r["tool_calls"] and r["tool_calls"][0]["tool"] == "incidents"
    assert r["tool_calls"][0]["tool"] == "incidents"
    assert "crimp_height" in r["answer"] and "vision_false_reject" in r["answer"]


def test_defect_codes_route_to_right_sop(plant):
    # regression: underscored defect codes used to be one token and missed the vision SOP
    assert plant.search_sops("vision_false_reject Line 3")["results"][0]["doc"] == "vision_false_rejects.md"
    assert plant.search_sops("crimp_height Line 2")["results"][0]["doc"] == "crimp_height_out_of_spec.md"
