from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import treesummary

app = Flask(__name__)
CORS(app)


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    directory = data["directory"]
    config_path = data.get("config", "config.json")

    with open(config_path, "r") as config_file:
        config = json.load(config_file)

    # Initialize AWS Bedrock client (you might need to handle AWS credentials)
    bedrock_client = treesummary.boto3.client(
        service_name="bedrock-runtime",
        region_name=config["aws_region"],
        config=treesummary.Config(retries={"max_attempts": 5, "mode": "standard"}),
    )

    results = treesummary.process_directory(
        directory,
        bedrock_client,
        config,
        file_limit=config.get("limit"),
        parallel=config.get("parallel", 1),
        supersummary_interval=config.get("supersummary_interval"),
        state_file="treesummary_state.pkl",
        restart=False,
    )

    summaries = {}
    supersummaries = []
    for result_type, result in results:
        if result_type == "summaries":
            summaries = result
        elif result_type == "supersummary":
            supersummaries.append(result)

    if config.get("generate_final_summary"):
        final_summary = treesummary.generate_final_summary(
            supersummaries, bedrock_client, config
        )
    else:
        final_summary = None

    if config.get("generate_modernisation_summary"):
        modernisation_summary = treesummary.generate_modernisation_summary(
            summaries, bedrock_client, config
        )
    else:
        modernisation_summary = None

    return jsonify(
        {
            "summaries": summaries,
            "supersummaries": supersummaries,
            "final_summary": final_summary,
            "modernisation_summary": modernisation_summary,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
