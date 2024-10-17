# Tree Summary

This script generates a summary of code within a directory tree. It will generate a summary of each file (matching the configured extensions) and generate a summary of summaries every n summaries (configurable in `config.json`) in Markdown

Usage:

1. Edit config.json with your desired settings.
2. Install deps `pip install -r requirements.txt`
3. Run `python3 treesummary.py <path>`.

Where `<path>` is the path to the directory containing the code.

For example output see [example_output](example_output).

Requirements:

- Python 3.12.x
- AWS Bedrock Access (via `aws sso login`)

Author: Sam McLeod
