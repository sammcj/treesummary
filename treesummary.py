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
import pickle


def load_state(state_file: str) -> Dict[str, Any]:
    if os.path.exists(state_file):
        with open(state_file, "rb") as f:
            return pickle.load(f)
    return {"processed_files": set(), "last_directory": None}


def save_state(state_file: str, state: Dict[str, Any]):
    with open(state_file, "wb") as f:
        pickle.dump(state, f)


def get_directory_tree(
    path: str, max_depth: int = 3, ignore_paths: List[str] = []
) -> str:
    tree = []
    for root, dirs, files in os.walk(path):
        level = root.replace(path, "").count(os.sep)
        if level > max_depth:
            continue

        # Check if the current directory should be ignored
        if any(ignored_path in root for ignored_path in ignore_paths):
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
            "content": [{"text": f"{config['file_prompt']}\n\n{context}"}],
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
        print(f"ERROR: Can't invoke '{config['model_id']}'. Reason: {e}")
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
            "content": [{"text": f"{config['summary_prompt']}\n\n{context}"}],
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
        print(f"ERROR: Can't invoke '{config['model_id']}'. Reason: {e}")
        return f"Error summarising summaries: {e}"


def process_directory(
    directory: str,
    bedrock_client: Any,
    config: Dict[str, Any],
    file_limit: int,
    parallel: int,
    supersummary_interval: int,
    state_file: str,
    restart: bool,
) -> Dict[str, str]:
    project_tree = get_directory_tree(
        directory, ignore_paths=config.get("ignore_paths", [])
    )
    summaries = {}
    files_to_process = []

    state = (
        load_state(state_file)
        if not restart
        else {"processed_files": set(), "last_directory": None}
    )

    if state["last_directory"] != directory:
        state["processed_files"] = set()
    state["last_directory"] = directory

    print(f"Scanning directory: {directory}")
    print(f"File extensions to process: {config['file_extensions']}")
    print(f"Paths to ignore: {config.get('ignore_paths', [])}")

    for root, _, files in os.walk(directory):
        if any(ignored_path in root for ignored_path in config.get("ignore_paths", [])):
            if config["verbose"] == True:
                print(f"Ignoring directory: {root}")
            continue

        for file in files:
            if any(file.endswith(ext) for ext in config["file_extensions"]):
                file_path = os.path.join(root, file)
                if file_path not in state["processed_files"]:
                    files_to_process.append(file_path)

    print(f"Total files found to process: {len(files_to_process)}")

    if not files_to_process:
        print(
            "No files found to process. Check your file extensions in the config and ignore_paths setting."
        )
        return

    # Determine if we're processing all files or using a limit
    process_all = file_limit is None or file_limit == 0
    if process_all:
        print("Processing all files (no limit)")
    else:
        print(f"Processing files with a limit of {file_limit}")

    while files_to_process:
        if process_all:
            current_batch = files_to_process
            files_to_process = []
        else:
            current_batch = files_to_process[:file_limit]
            files_to_process = files_to_process[file_limit:]

        print(f"Processing batch of {len(current_batch)} files")

        def process_file(file_path):
            print(f"Processing file: {file_path}")
            return file_path, summarise_file(
                file_path, bedrock_client, config, project_tree
            )

        with ThreadPoolExecutor(max_workers=parallel) as executor:
            future_to_file = {
                executor.submit(process_file, file_path): file_path
                for file_path in current_batch
            }

            for i, future in enumerate(
                tqdm.tqdm(
                    as_completed(future_to_file),
                    total=len(current_batch),
                    desc="Processing files",
                )
            ):
                file_path, summary = future.result()
                summaries[file_path] = summary
                state["processed_files"].add(file_path)

                if supersummary_interval and (
                    len(state["processed_files"]) % supersummary_interval == 0
                ):
                    print("Generating supersummary...")
                    supersummary = summarise_summaries(
                        summaries, bedrock_client, config
                    )
                    yield "supersummary", supersummary

                save_state(state_file, state)

        # Generate supersummary after processing the batch
        if supersummary_interval:
            print("Generating supersummary after batch completion...")
            supersummary = summarise_summaries(summaries, bedrock_client, config)
            yield "supersummary", supersummary

        if not process_all and files_to_process:
            continue_processing = (
                input(
                    f"Processed {file_limit} files. Continue for another {file_limit} files? (y/n): "
                ).lower()
                == "y"
            )
            if not continue_processing:
                break

    print(f"Total files processed: {len(summaries)}")
    yield "summaries", summaries


def save_to_markdown(results: Dict[str, str], output_file: str):
    with open(output_file, "w", encoding="utf-8") as f:
        for file, summary in results.items():
            # Escape any existing # characters in the file path
            safe_file_path = file.replace("#", "\\#")
            f.write(f"# File: {safe_file_path}\n\n")
            f.write("## Summary:\n\n")

            # Split the summary into lines and properly format any list items or code blocks
            lines = summary.split("\n")
            in_code_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    f.write(line + "\n")
                elif in_code_block:
                    f.write(line + "\n")
                else:
                    # Ensure list items are on their own line
                    if line.strip().startswith(("- ", "* ", "1. ")):
                        f.write("\n" + line + "\n")
                    else:
                        f.write(line + "\n")

            f.write("\n---\n\n")


def generate_final_summary(
    supersummaries: List[str],
    bedrock_client: Any,
    config: Dict[str, Any],
) -> str:
    context = "\n\n".join(
        [f"Supersummary {i+1}:\n{summary}" for i, summary in enumerate(supersummaries)]
    )

    conversation = [
        {
            "role": "user",
            "content": [{"text": f"{config['final_summary_prompt']}\n\n{context}"}],
        }
    ]

    try:
        response = bedrock_client.converse(
            modelId=config["model_id"],
            messages=conversation,
            system=[{"text": config["system_prompt"]}],
            inferenceConfig={
                "maxTokens": config["final_summary_max_tokens"],
                "temperature": config["temperature"],
                "topP": config["top_p"],
            },
        )

        response_text = response["output"]["message"]["content"][0]["text"]
        return response_text

    except ClientError as e:
        print(f"ERROR: Can't invoke '{config['model_id']}'. Reason: {e}")
        return f"Error generating final summary: {e}"


def main():
    parser = argparse.ArgumentParser(description="Code Summarisation Tool")
    parser.add_argument("directory", help="Path to the project directory")
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(__file__), "config.json"),
        help="Path to the configuration file",
    )
    parser.add_argument(
        "--clear-state",
        action="store_true",
        help="Clear the state and restart processing",
    )
    args = parser.parse_args()

    with open(args.config, "r") as config_file:
        config = json.load(config_file)

    # Override config with CLI args
    for arg, value in vars(args).items():
        if value is not None:
            config[arg] = value

    # Set file_limit to None if it's 0 or not set
    file_limit = config.get("limit")
    if file_limit == 0:
        file_limit = None

    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=config["aws_region"],
        config=Config(retries={"max_attempts": 5, "mode": "standard"}),
    )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"summary_output_{timestamp}.md")
    supersummary_file = os.path.join(output_dir, f"supersummary_{timestamp}.md")
    final_summary_file = os.path.join(output_dir, f"final_summary_{timestamp}.md")
    state_file = os.path.join(output_dir, "treesummary_state.pkl")

    if not args.restart and os.path.exists(state_file):
        resume = (
            input(
                "Previous processing state found. The last directory processed was: "
                + f"{load_state(state_file)['last_directory']}. "
                + "Would you like to resume processing? (y/n): "
            ).lower()
            == "y"
        )
        if not resume:
            args.restart = True

    supersummaries = []
    for result_type, result in process_directory(
        config["directory"],
        bedrock_client,
        config,
        file_limit,
        config.get("parallel"),
        config.get("supersummary_interval"),
        state_file,
        args.restart,
    ):
        if result_type == "summaries":
            save_to_markdown(result, output_file)
            print(f"Results have been saved to {output_file}")
        elif result_type == "supersummary":
            supersummaries.append(result)
            with open(supersummary_file, "a") as f:
                f.write(f"# Supersummary\n\n{result}\n\n---\n\n")
            print(f"Supersummary has been appended to {supersummary_file}")

    if os.path.exists(state_file):
        state = load_state(state_file)
        print(f"Total files processed: {len(state['processed_files'])}")

    if config.get("generate_final_summary") == True:
        print("Generating final summary...")
        final_summary = generate_final_summary(supersummaries, bedrock_client, config)
        with open(final_summary_file, "w") as f:
            f.write(f"# Final Summary\n\n{final_summary}")
        print(f"Final summary has been saved to {final_summary_file}")


if __name__ == "__main__":
    main()
