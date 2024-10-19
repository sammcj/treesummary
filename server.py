from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import treesummary

app = Flask(__name__, static_folder="web-interface", static_url_path="")
CORS(app)


@app.route("/")
def index():
    print("Serving index.html")
    return app.send_static_file("index.html")


@app.route("/<path:path>")
def serve_static(path):
    print(f"Serving static file: {path}")
    return send_from_directory("web-interface", path)


@app.route("/api/file-tree")
def get_file_tree():
    print("Fetching file tree")
    root_dir = os.path.abspath(os.path.dirname(__file__))
    tree = build_file_tree(root_dir)
    print("File tree:", json.dumps(tree, indent=2))  # Log the file tree
    return jsonify(tree)


def build_file_tree(path):
    print(f"Building file tree for: {path}")
    tree = {}
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                tree[item] = build_file_tree(item_path)
            else:
                tree[item] = None
    except PermissionError:
        print(f"Permission denied: {path}")
    except Exception as e:
        print(f"Error accessing {path}: {str(e)}")
    return tree


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
            abs_path = os.path.abspath(file_or_dir)
            if os.path.isdir(abs_path):
                # If it's a directory, process all files within it
                for root, _, files in os.walk(abs_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if any(file.endswith(ext) for ext in config["file_extensions"]):
                            summary = treesummary.summarise_file(
                                file_path, bedrock_client, config, ""
                            )
                            bucket_results["summaries"][file_path] = summary
            elif os.path.isfile(abs_path):
                # If it's a file, process it directly
                summary = treesummary.summarise_file(
                    abs_path, bedrock_client, config, ""
                )
                bucket_results["summaries"][abs_path] = summary
            else:
                print(f"Warning: {abs_path} is neither a file nor a directory")

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
    print("Starting Flask server on http://localhost:5000")
    app.run(debug=True)
