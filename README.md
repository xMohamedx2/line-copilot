# Line Copilot

A small AI assistant for production and quality engineers on a connector assembly line. You ask questions like "what looks wrong in the data?" and it calls analytics tools, finds the problem, pulls the matching troubleshooting procedure, and shows exactly which tool results its answer came from.

**All data and SOPs in this repo are synthetic.** Nothing here is Molex data or a Molex procedure. It is a learning project I built to practice the full AI solution lifecycle: find a problem, build a prototype, test it, and measure how well it works.

## What it does

- Generates 14 days of hourly production data for 3 lines and 3 shifts (units, defects by type, downtime and reasons).
- Two problems are planted on purpose so the system can be checked against known answers:
  1. Line 2: crimp height drifts out of spec on days 8 to 10.
  2. Line 3, Night shift: vision lighting degrades from day 11 (false rejects and vision faults).
- Tools: KPI summary, downtime ranking, defect pareto, anomaly detection (robust z-score per line and shift), incident rollup, SOP search (TF-IDF).
- Agent: with `ANTHROPIC_API_KEY` set, Claude decides which tools to call (tool-use loop over the Messages API). Without a key, a keyword router calls the same tools, so the demo and tests run offline.
- Web UI (Flask) with an incident table and a chat box. Every answer has an expandable list of the tool calls and raw results behind it.

## Run it

```bash
pip install flask pandas numpy scikit-learn requests pytest
python -m linecopilot.datagen     # writes data/production.csv
python app.py                     # http://localhost:5050
# optional: export ANTHROPIC_API_KEY=...  (and LINECOPILOT_MODEL=<model id>)
pytest -q
python eval.py
```

## How I checked it

- 10 unit tests: KPI totals against raw pandas, filters, pareto sums to 100 percent, both planted problems detected, SOP routing, filter parsing, and the offline agent calling the right tool.
- `eval.py` compares detection against the planted ground truth: 13 of 13 planted line/shift/day cells found, 1 false positive (Line 3 Swing day 12), so recall 1.00 and precision 0.93.
- Two bugs found while building, both now covered by tests:
  - The first pareto credited all defects in an hour to the top defect type, which made one type look like 100 percent. Fixed by storing per-type counts.
  - Defect codes like `vision_false_reject` were one search token, so the wrong SOP was returned. Fixed by splitting on underscores, with a regression test.

## Limits

- Synthetic data with planted, obvious problems. Real data is messier, so real precision would be lower.
- The offline router is keyword based and only handles the question shapes it was written for. LLM mode is the flexible path, but I have not scored it against a question set yet.
- SOP search is TF-IDF over 5 short documents. A real version would need embeddings, document versioning and access control.
- No authentication, no live data connection, no monitoring.

## Next steps

- Score LLM mode on a fixed question set (answer matches tool output, no invented numbers).
- Replace the CSV with a read-only database connection and add data quality checks.
- Add statistical process control charts and capability metrics.
- Containerize it and add CI that runs the tests and eval.
