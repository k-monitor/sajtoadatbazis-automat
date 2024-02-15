from flask import Flask, request, jsonify
import random

app = Flask(__name__)

@app.route("/complete", methods=["POST"])
def index():
    data = request.get_json()
    if random.random() > 0.5:
        return jsonify({"content": "korrupció"}), 200
    return jsonify({"content": "egyéb"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8085)