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
    buckets = data["buckets"]
    settings = data["settings"]

    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    # Update config with settings from the frontend
    config.update(settings)

    # Initialize AWS Bedrock client (you might need to handle AWS credentials)
    bedrock_client = treesummary.boto3.client(
        service_name="bedrock-runtime",
        region_name=config["aws_region"],
        config=treesummary.Config(retries={"max_attempts": 5, "mode": "standard"}),
    )

    results = []
    for bucket in buckets:
        bucket_results = {"name": bucket["name"], "summaries": {}, "supersummary": None}

        for file_or_dir in bucket["files"]:
            if os.path.isdir(file_or_dir):
                # If it's a directory, process all files within it
                for root, _, files in os.walk(file_or_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if any(file.endswith(ext) for ext in config["file_extensions"]):
                            summary = treesummary.summarise_file(
                                file_path, bedrock_client, config, ""
                            )
                            bucket_results["summaries"][file_path] = summary
            else:
                # If it's a file, process it directly
                summary = treesummary.summarise_file(
                    file_or_dir, bedrock_client, config, ""
                )
                bucket_results["summaries"][file_or_dir] = summary

        # Generate supersummary for the bucket
        if config.get("supersummary_interval"):
            bucket_results["supersummary"] = treesummary.summarise_summaries(
                bucket_results["summaries"], bedrock_client, config
            )

        results.append(bucket_results)

    # Generate final summary and modernisation summary if requested
    final_summary = None
    modernisation_summary = None

    if config.get("generate_final_summary"):
        final_summary = treesummary.generate_final_summary(
            [b["supersummary"] for b in results if b["supersummary"]],
            bedrock_client,
            config,
        )

    if config.get("generate_modernisation_summary"):
        all_summaries = {f: s for b in results for f, s in b["summaries"].items()}
        modernisation_summary = treesummary.generate_modernisation_summary(
            all_summaries, bedrock_client, config
        )

    return jsonify(
        {
            "buckets": results,
            "final_summary": final_summary,
            "modernisation_summary": modernisation_summary,
        }
    )

if __name__ == "__main__":
    app.run(debug=True)
