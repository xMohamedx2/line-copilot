"""Tool-using agent.

Two modes:
  * LLM mode: if ANTHROPIC_API_KEY is set, Claude decides which tools to call
    (Messages API tool use loop, plain HTTPS, no SDK needed).
  * Offline mode: a small keyword router calls the same tools and writes a
    templated answer. This keeps the demo and tests working with no key or network.

The answer always includes the tool results it was based on, so a person can check them.
"""
from __future__ import annotations

import json
import os
import re

import requests

from .tools import TOOL_SPECS, Plant

MODEL = os.environ.get("LINECOPILOT_MODEL", "claude-sonnet-4-5")
SYSTEM = (
    "You are Line Copilot, an assistant for production and quality engineers. "
    "Answer only from tool results. Always call tools before stating numbers. "
    "If the data does not support an answer, say so. When you find a problem, "
    "search the SOPs and give the next steps. Be concise and say which tool results you used. "
    "Days are numbered 1-14. This is a synthetic-data demo."
)


def _call_tool(plant: Plant, name: str, args: dict) -> dict:
    fn = getattr(plant, name, None)
    if name not in {t["name"] for t in TOOL_SPECS} or fn is None:
        return {"error": f"unknown tool {name}"}
    try:
        return fn(**args)
    except TypeError as e:
        return {"error": f"bad arguments: {e}"}


def ask_llm(plant: Plant, question: str, max_steps: int = 6) -> dict:
    key = os.environ["ANTHROPIC_API_KEY"]
    messages = [{"role": "user", "content": question}]
    trace = []
    for _ in range(max_steps):
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": 1200, "system": SYSTEM, "tools": TOOL_SPECS, "messages": messages},
            timeout=60,
        )
        r.raise_for_status()
        body = r.json()
        messages.append({"role": "assistant", "content": body["content"]})
        if body["stop_reason"] != "tool_use":
            text = "".join(b["text"] for b in body["content"] if b["type"] == "text")
            return {"mode": "llm", "answer": text, "tool_calls": trace}
        results = []
        for b in body["content"]:
            if b["type"] == "tool_use":
                out = _call_tool(plant, b["name"], b["input"])
                trace.append({"tool": b["name"], "args": b["input"], "result": out})
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": json.dumps(out)})
        messages.append({"role": "user", "content": results})
    return {"mode": "llm", "answer": "Stopped after too many tool steps.", "tool_calls": trace}


# ---------------------------------------------------------------- offline
def _parse_filters(q: str) -> dict:
    f = {}
    m = re.search(r"line\s*([123])", q, re.I)
    if m:
        f["line"] = f"Line {m.group(1)}"
    for s in ("night", "swing", "day"):
        if re.search(rf"\b{s}\b(?:\s+shift)?", q, re.I) and not (s == "day" and re.search(r"day\s*\d", q, re.I)):
            f["shift"] = s.capitalize()
            break
    m = re.search(r"days?\s*(\d+)\s*(?:-|to|through)\s*(\d+)", q, re.I)
    if m:
        f["day_from"], f["day_to"] = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"day\s*(\d+)", q, re.I)
        if m:
            f["day_from"] = f["day_to"] = int(m.group(1))
    return f


def ask_offline(plant: Plant, question: str) -> dict:
    q, f, trace = question.lower(), _parse_filters(question), []

    def run(name, **kw):
        out = _call_tool(plant, name, kw)
        trace.append({"tool": name, "args": kw, "result": out})
        return out

    lines = []
    if re.search(r"anomal|problem|wrong|issue|spike|unusual|root cause|investigate", q):
        res = run("incidents")["incidents"]
        if not res:
            lines.append("No line/shift/day stands out from its own baseline.")
        else:
            lines.append(f"{len(res)} incident(s) found versus each line and shift's own baseline:")
            for a in res:
                lines.append(
                    f"- {a['line']}: {a['main_defect']} on {', '.join(a['shifts'])} shift(s), days {a['first_day']}-{a['last_day']}. "
                    f"Peak defect rate {a['peak_defect_rate_pct']}% (baseline {a['baseline_pct']}%), {a['downtime_min']} min downtime in flagged cells."
                )
            for a in res[:2]:
                sop = run("search_sops", query=f"{a['main_defect']} {a['line']}")["results"]
                if sop:
                    lines.append(f"\n{a['main_defect']}: suggested next steps from {sop[0]['doc']}:")
                    lines += [l for l in sop[0]["text"].splitlines() if re.match(r"\d\.", l)]
    elif re.search(r"downtime|stop|down\b", q):
        res = run("top_downtime", **f)["top_reasons"]
        lines.append("Top downtime reasons: " + "; ".join(f"{r['reason']} {r['minutes']} min ({r['events']} events)" for r in res))
    elif re.search(r"pareto|defect type|which defect|top defect|biggest defect", q):
        res = run("defect_pareto", **f)["pareto"]
        lines.append("Defect pareto: " + "; ".join(f"{r['defect']} {r['pct']}%" for r in res))
    elif re.search(r"compare|versus|vs\b|shift", q) and "shift" not in f:
        res = run("compare_shifts", **{k: v for k, v in f.items() if k != "shift"})["by_shift"]
        lines.append("By shift: " + "; ".join(f"{s} defect {r['defect_rate_pct']}%, downtime {r['downtime_min']} min" for s, r in res.items()))
    elif re.search(r"how to|fix|procedure|sop|troubleshoot|steps|what should", q):
        res = run("search_sops", query=question)["results"]
        lines.append(res[0]["text"] if res else "No matching SOP found.")
    else:
        r = run("kpi_summary", **f)
        if "error" in r:
            lines.append(r["error"])
        else:
            lines.append(f"{r['units']} units, {r['defects']} defects ({r['defect_rate_pct']}%), {r['downtime_min']} min downtime over {r['downtime_events']} events.")
    return {"mode": "offline", "answer": "\n".join(lines), "tool_calls": trace}


def ask(plant: Plant, question: str) -> dict:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return ask_llm(plant, question)
        except Exception as e:  # network or API problem: fall back instead of failing
            out = ask_offline(plant, question)
            out["note"] = f"LLM call failed ({type(e).__name__}); used offline mode."
            return out
    return ask_offline(plant, question)
