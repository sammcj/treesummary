# Tree Summary

This script generates a summary of code within a directory tree. It will generate a summary of each file (matching the configured extensions) and generate a summary of summaries every n summaries (configurable in `config.json`) in Markdown

Currently only supports Amazon Bedrock for the LLM, will add OpenAI compatiable API support in the future.

Usage:

1. Edit config.json with your desired settings.
2. Install deps `pip install -r requirements.txt`
3. Run `python3 treesummary.py <path>`.

Where `<path>` is the path to the directory containing the code.

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

## Example Output

For example output see [example_output](example_output).

```shell
python treesummary.py .                                                                                                      (mainU)
Total files found to process: 1
Starting fresh processing of 1 files.
Processing batch of 1 files.
Attempting to run ingest on 1 files.
Running ingest command: ingest ./treesummary.py
Ingest command output:

⠋ Traversing directory and building tree..  [0s] [ℹ️] Top 10 largest files (by estimated token count):
- 1. /Users/samm/git/sammcj/treesummary/treesummary.py (3,737 tokens)

[✅] Copied to clipboard successfully.
[ℹ️] Tokens (Approximate): 3,782

Extracted token count: 3782
Estimated total tokens for this batch: 3782
Processing batch of 1 files.
Processing files: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1/1 [00:06<00:00,  6.59s/it]
Results have been saved to /Users/samm/git/sammcj/treesummary/output/summary_output_20241017-1854.md
Total files processed: 1
Generating final summary...
```

## Requirements

- Python 3.12.x
- AWS Bedrock Access (via `aws sso login`)

Author: Sam McLeod
