import os
import json
import argparse
from typing import Dict, List, Any
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm
from datetime import datetime
import markdown


def get_directory_tree(path: str, max_depth: int = 3) -> str:
    tree = []
    for root, dirs, files in os.walk(path):
        level = root.replace(path, "").count(os.sep)
        if level > max_depth:
            continue
        indent = "  " * level
        tree.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = "  " * (level + 1)
        for file in files:
            tree.append(f"{sub_indent}{file}")
    return "\n".join(tree)


def get_files_in_directory(directory: str) -> List[str]:
    return [
        f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))
    ]


def summarise_file(
    file_path: str,
    bedrock_client: Any,
    config: Dict[str, Any],
    project_tree: str,
) -> str:
    with open(file_path, "r") as file:
        content = file.read()

    directory = os.path.dirname(file_path)
    files_in_directory = get_files_in_directory(directory)

    context = f"""
Project Structure:
{project_tree}

Files in the same directory as {os.path.basename(file_path)}:
{', '.join(files_in_directory)}

File Content:
{content}
    """

    conversation = [
        {
            "role": "user",
            "content": [{"text": f"{config["file_prompt"]}\n\n{context}"}],
        }
    ]

    try:
        response = bedrock_client.converse(
            modelId=config["model_id"],
            messages=conversation,
            system=[{"text": config["system_prompt"]}],
            inferenceConfig={
                "maxTokens": config["max_tokens"],
                "temperature": config["temperature"],
                "topP": config["top_p"],
            },
        )

        response_text = response["output"]["message"]["content"][0]["text"]
        return response_text

    except ClientError as e:
        print(f"ERROR: Can't invoke '{config["model_id"]}'. Reason: {e}")
        return f"Error summarising file: {e}"


def summarise_summaries(
    summaries: Dict[str, str],
    bedrock_client: Any,
    config: Dict[str, Any],
) -> str:
    context = "\n\n".join(
        [f"File: {file}\nSummary: {summary}" for file, summary in summaries.items()]
    )

    conversation = [
        {
            "role": "user",
            "content": [{"text": f"{config["summary_prompt"]}\n\n{context}"}],
        }
    ]

    try:
        response = bedrock_client.converse(
            modelId=config["model_id"],
            messages=conversation,
            system=[{"text": config["system_prompt"]}],
            inferenceConfig={
                "maxTokens": config["max_tokens"],
                "temperature": config["temperature"],
                "topP": config["top_p"],
            },
        )

        response_text = response["output"]["message"]["content"][0]["text"]
        return response_text

    except ClientError as e:
        print(f"ERROR: Can't invoke '{config["model_id"]}'. Reason: {e}")
        return f"Error summarising summaries: {e}"


def process_directory(
    directory: str,
    bedrock_client: Any,
    config: Dict[str, Any],
    file_limit: int,
    parallel: int,
    supersummary_interval: int,
) -> Dict[str, str]:
    project_tree = get_directory_tree(directory)
    summaries = {}
    files_to_process = []

    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in config["file_extensions"]):
                file_path = os.path.join(root, file)
                files_to_process.append(file_path)

    if file_limit and len(files_to_process) > file_limit:
        files_to_process = files_to_process[:file_limit]

    def process_file(file_path):
        return file_path, summarise_file(
            file_path,
            bedrock_client,
            config,
            project_tree,
        )

    with ThreadPoolExecutor(max_workers=parallel) as executor:
        future_to_file = {
            executor.submit(process_file, file_path): file_path
            for file_path in files_to_process
        }

        for i, future in enumerate(
            tqdm.tqdm(
                as_completed(future_to_file),
                total=len(files_to_process),
                desc="Processing files",
            )
        ):
            file_path, summary = future.result()
            summaries[file_path] = summary

            if supersummary_interval and (i + 1) % supersummary_interval == 0:
                supersummary = summarise_summaries(
                    summaries,
                    bedrock_client,
                    config,
                )
                yield "supersummary", supersummary

    yield "summaries", summaries


def save_to_markdown(results: Dict[str, str], output_file: str):
    with open(output_file, "w") as f:
        for file, summary in results.items():
            f.write(f"# File: {file}\n\n## Summary:\n\n{summary}\n\n---\n\n")


def main():
    parser = argparse.ArgumentParser(description="Code Summarisation Tool")
    parser.add_argument("directory", help="Path to the project directory")
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(__file__), "config.json"),
        help="Path to the configuration file",
    )
    args = parser.parse_args()

    with open(args.config, "r") as config_file:
        config = json.load(config_file)

    # Override config with CLI args
    for arg, value in vars(args).items():
        if value is not None:
            config[arg] = value

    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=config["aws_region"],
        config=Config(retries={"max_attempts": 5, "mode": "standard"}),
    )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    output_file = os.path.join(
        os.path.dirname(__file__), f"output/summary_output_{timestamp}.md"
    )
    supersummary_file = os.path.join(
        os.path.dirname(__file__), f"output/supersummary_{timestamp}.md"
    )

    for result_type, result in process_directory(
        config["directory"],
        bedrock_client,
        config,
        config.get("limit"),
        config.get("parallel", 1),
        config.get("supersummary_interval"),
    ):
        if result_type == "summaries":
            save_to_markdown(result, output_file)
            print(f"Results have been saved to {output_file}")
        elif result_type == "supersummary":
            with open(supersummary_file, "a") as f:
                f.write(f"# Supersummary\n\n{result}\n\n---\n\n")
            print(f"Supersummary has been appended to {supersummary_file}")


if __name__ == "__main__":
    main()
