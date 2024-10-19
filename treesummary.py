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
import subprocess
import shutil
import glob

# ... (keep all the existing imports and other functions)

def summarise_file(
    file_path: str,
    bedrock_client: Any,
    config: Dict[str, Any],
    project_tree: str,
) -> Dict[str, str]:
    try:
        abs_path = os.path.abspath(file_path)
        with open(abs_path, "r", encoding="utf-8") as file:
            content = file.read()

        directory = os.path.dirname(abs_path)
        files_in_directory = get_files_in_directory(directory)

        context = f"""
Project Structure:
{project_tree}

Files in the same directory as {os.path.basename(abs_path)}:
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

            summary = response["output"]["message"]["content"][0]["text"]

            result = {"summary": summary}

            if config.get("generate_file_modernisation_recommendations", False):
                modernisation_conversation = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": f"{config['file_modernisation_prompt']}\n\n{context}"
                            }
                        ],
                    }
                ]

                modernisation_response = bedrock_client.converse(
                    modelId=config["model_id"],
                    messages=modernisation_conversation,
                    system=[{"text": config["system_prompt"]}],
                    inferenceConfig={
                        "maxTokens": config["max_tokens"],
                        "temperature": config["temperature"],
                        "topP": config["top_p"],
                    },
                )

                modernisation_recommendations = modernisation_response["output"][
                    "message"
                ]["content"][0]["text"]
                result["modernisation_recommendations"] = modernisation_recommendations

            return result

        except ClientError as e:
            print(f"ERROR: Can't invoke '{config['model_id']}'. Reason: {e}")
            return {"summary": f"Error summarising file: {e}"}

    except FileNotFoundError:
        print(f"ERROR: File not found: {abs_path}")
        return {"summary": f"Error: File not found: {abs_path}"}
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while processing {abs_path}: {e}")
        return {
            "summary": f"Error: An unexpected error occurred while processing the file: {e}"
        }

# ... (keep all the other existing functions)

if __name__ == "__main__":
    main()
