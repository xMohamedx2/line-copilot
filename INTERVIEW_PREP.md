# Molex AI Solutions Engineer: interview prep using Line Copilot

Source for the role: public listing for "AI Solutions Engineer (Early Career)", Rochester Hills MI or Lisle IL. It describes working with Molex's corporate AI Digital Team, building AI solutions that improve engineering productivity and manufacturing performance, the full lifecycle from prototype to deployment to measuring impact, and experience with AI-assisted dev tools and engineering practices like version control and DevOps. Re-read the actual posting you applied to, since wording may differ.

## 30-second pitch for the project

"I work nights on a battery production line as the vision systems escalation point, so I see how much time goes into figuring out what changed and what the procedure says. I built a small prototype, Line Copilot, on synthetic connector line data. You ask what looks wrong, it runs analytics tools, finds the problem, pulls the matching SOP steps, and shows the tool results behind every answer. I tested it against planted problems so I could measure it, not just demo it."

## How it maps to the role

| Posting theme | What to point at |
|---|---|
| End-to-end AI solution | Data generation, tools, agent, UI, tests, eval, README |
| Full lifecycle, measure impact | `eval.py`: recall 1.00, precision 0.93 vs planted ground truth. Be clear that real data would be harder |
| AI-assisted development | Built it with Claude as a coding partner. Say what you verified yourself |
| Engineering practices | Tests, regression test for a real bug, README with limits. Put it in Git |
| Manufacturing domain | Your LG work: escalations, downtime analysis, dashboards, the 45 to 15 minute downtime reduction |
| Work with stakeholders | You brief production and plant managers and write escalation reports |

## Design decisions to be ready to explain

1. **Tools instead of letting the model do math.** Numbers come from pandas functions, the LLM only picks tools and explains. That is why answers can be checked.
2. **Shows its work.** Each answer exposes tool calls and raw results. Engineers will not trust a number they cannot trace.
3. **Offline fallback.** Works without a key or network, which also made it testable.
4. **Robust z-score (median and MAD).** A plain mean and standard deviation get pulled up by the anomalies themselves.
5. **Incident rollup.** Raw anomalies listed nine Line 2 cells before the Line 3 problem. Grouping by line and defect made the output useful.

## Bugs to tell honestly (good story)

- The pareto attributed all of an hour's defects to its top defect type, so one type showed 100 percent. Caught it by sanity checking the output, fixed with per-type counts.
- Search returned the changeover SOP for a vision problem because `vision_false_reject` was a single token. Caught by reading the output, fixed and added a regression test.

## Likely questions and honest answers

- **"Did you deploy this?"** No. It is a local prototype on synthetic data. Say what deployment would need: real data connection, auth, monitoring, CI, and a pilot with a few engineers.
- **"How would you know it works on real data?"** Backtest on past incidents with known root causes, track false alarm rate, have engineers rate answers, compare time to find root cause with and without it.
- **"What about hallucinations?"** Numbers only come from tools, system prompt says to answer only from tool results, answers cite the tool output. Next step is a scored question set. Admit LLM mode is not scored yet.
- **"Why not just a dashboard?"** Dashboards need you to know where to look. This is for the first question, "what changed", plus linking to the procedure. It complements dashboards (you have built several).
- **"What would you build next for Molex?"** Ask them first: where do engineers lose the most time? Then pick one workflow, pilot it, and measure. Do not claim to know their systems.
- **"Weakness?"** Limited ML modeling and production software experience so far. You are strongest at manufacturing data, vision systems and turning data into decisions. Name what you are doing to close the gap.

## Questions to ask them

- What does the AI Digital Team's path from idea to pilot to production look like, and where does it usually stall?
- Which manufacturing or engineering workflows are the team prioritizing right now?
- How do you measure whether an AI solution created value?
- How much of the work is with plant users versus central data and platform teams?
- What does success look like in the first 6 months?

## Before the interview

- [ ] Put the project on GitHub with the README (xMohamedx2).
- [ ] Run it once end to end and rehearse a 3 minute demo: "what looks wrong", then "top downtime on Line 3 night shift", then open the tool-call details.
- [ ] If you have an Anthropic API key, run it in LLM mode and note one good answer and one weak one to talk about.
- [ ] Do not describe it as production or Molex data. Say synthetic, prototype, learning project.
