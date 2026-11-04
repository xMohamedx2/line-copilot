from flask import Flask, jsonify, request, send_from_directory

from linecopilot.agent import ask
from linecopilot.tools import Plant

app = Flask(__name__, static_folder="static")
plant = Plant()


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.post("/api/ask")
def api_ask():
    q = (request.get_json(silent=True) or {}).get("question", "").strip()
    if not q:
        return jsonify({"error": "question is required"}), 400
    return jsonify(ask(plant, q))


@app.get("/api/overview")
def overview():
    return jsonify({
        "kpi": plant.kpi_summary(),
        "by_line": {l: plant.kpi_summary(line=l) for l in ["Line 1", "Line 2", "Line 3"]},
        "incidents": plant.incidents()["incidents"],
    })


if __name__ == "__main__":
    app.run(port=5050, debug=False)
