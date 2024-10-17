# Tree Summary

This script generates a summary of code within a directory tree. It will generate a summary of each file (matching the configured extensions) and generate a summary of summaries every n summaries (configurable in `config.json`) in Markdown

Currently only supports Amazon Bedrock for the LLM, will add OpenAI compatiable API support in the future.

Usage:

1. Edit config.json with your desired settings.
2. Install deps `pip install -r requirements.txt`
3. Run `python3 treesummary.py <path>`.

Where `<path>` is the path to the directory containing the code.

For example output see [example_output](example_output).

State is stored in the output/treesummary_state.pkl file, so you can run the script multiple times to generate summaries for different directories or resume from a previous run.

## Config

- `aws_region`: The AWS region to use for the LLM
- `model_id`: The model ID to use for the LLM
- `file_extensions`: A list of file extensions to process
- `max_tokens`: The maximum number of tokens to generate
- `system_prompt`: The prompt to use for the system
- `file_prompt`: The prompt to use for each file
- `summary_prompt`: The prompt to use for the summary
- `limit`: The number of files to process (0 for all)
- `parallel`: The number of files to process in parallel
- `supersummary_interval`: The number of files to process before generating a supersummary
- `temperature`: The temperature sampling for the LLM
- `top_p`: The top_p sampling for the LLM
- `ignore_paths`: A list of paths to ignore

```json
{
  "aws_region": "ap-southeast-2",
  "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
  "file_extensions": [
    ".java",
    ".properties",
    ".go",
    ".py"
  ],
  "max_tokens": 2048,
  "system_prompt": "You are an AI assistant tasked with summarising (sometimes incomplete) code and providing insights into its structure and functionality. Your summaries should be concise yet informative, highlighting key components and their relationships while avoiding unnecessary prose. The goal is to help our development team understand the software in as short of a time as possible. You use British English spelling for any written text. ",
  "file_prompt": "Please summarise the following code, focusing on its main purpose, key components, and how it fits into the overall project structure. If the code is complex you may include a basic text-based diagram (using MermaidJS syntax) to illustrate the main classes or components and their relationships.",
  "summary_prompt": "Please provide a high-level summary of the project based on the individual file summaries. Include the name or path to the files included in the summary if you know them. Include a combined graph or diagram in MermaidJS that represents the overall structure and relationships between the main components of the project.",
  "limit": 0,
  "parallel": 4,
  "supersummary_interval": 4,
  "temperature": 0.35,
  "top_p": 0.90,
  "ignore_paths": [
    "node_modules",
    "vendor",
    ".git",
    ".idea",
    ".vscode",
    ".DS_Store",
    ".ipynb_checkpoints",
    "__pycache__",
    ".venv",
    "venv"
  ]
}
```

## Requirements

- Python 3.12.x
- AWS Bedrock Access (via `aws sso login`)

Author: Sam McLeod
