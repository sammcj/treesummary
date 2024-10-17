# File: /Users/samm/git/sammcj/ingest/template/template.go

## Summary:

The provided code is a Go package called `template` that handles the setup, reading, and rendering of templates for the `ingest` application. Here's a summary of the main components and functionality:

1. **SetupTemplate**: This function takes a template path as input and returns a `*template.Template` object. If the template path is empty, it will use a default template. The default template is either read from a user-specific location (`~/.config/ingest/patterns/templates/default.tmpl`) or from an embedded template if the user-specific template is not found.

2. **readTemplateFile**: This function reads the content of a template file from the specified path.

3. **getDefaultTemplate**: This function attempts to read the user-specific default template, and if not found, it returns the embedded default template.

4. **readEmbeddedTemplate**: This function returns the content of the embedded default template, which is a string containing a template for displaying source trees, files, and Git information.

5. **RenderTemplate**: This function takes a `*template.Template` object and a data map as input, and returns the rendered template as a string.

6. **PrintDefaultTemplate**: This function prints the content of the default template to the console.

The main purpose of this package is to provide a way to set up and render templates for the `ingest` application. The templates are used to display information about the source trees, files, and Git data in a formatted way. The default template is provided as a fallback, but users can also specify their own custom templates.

The package uses the `text/template` package from the Go standard library to handle the template parsing and rendering. It also utilizes the `github.com/fatih/color` and `github.com/mitchellh/go-homedir` packages for colored output and finding the user's home directory, respectively.

---

# File: /Users/samm/git/sammcj/ingest/token/token.go

## Summary:

This code is part of a Go package called "token" that provides functionality for working with text tokenization. Here's a summary of the main components and their purpose:

1. `GetTokenizer(encoding string) *tiktoken.Tiktoken`:
   - This function returns a tokenizer instance based on the specified encoding.
   - It supports various encodings like "o200k", "cl100k", "p50k", "r50k", and "gpt2".
   - If the encoding is not recognized, it defaults to "cl100k_base".
   - The tokenizer is obtained using the `tiktoken-go` library.

2. `GetModelInfo(encoding string) string`:
   - This function returns a string that provides information about the model associated with the given encoding.
   - It describes the type of models that use the specified encoding, such as OpenAI gpt-4o models, Llama3 and OpenAI ChatGPT models, OpenAI code models, and legacy models like GPT-3 and Davinci.

3. `CountTokens(rendered string, encoding string) int`:
   - This function counts the number of tokens in the provided "rendered" string using the specified encoding.
   - It first retrieves the appropriate tokenizer using the `GetTokenizer` function, and then encodes the input string to obtain the token count.
   - If the tokenizer cannot be obtained, the function returns 0.

The main purpose of this package is to provide a convenient way to work with text tokenization, which is an important aspect of natural language processing and language models. The `GetTokenizer` function allows you to obtain a tokenizer instance for a specific encoding, the `GetModelInfo` function provides helpful information about the models associated with each encoding, and the `CountTokens` function allows you to easily count the number of tokens in a given text.

This code is likely part of a larger project that involves working with language models and text processing, and the token package provides a reusable set of functions to handle these tasks.

---

# File: /Users/samm/git/sammcj/ingest/config/config.go

## Summary:

This code defines the configuration structure and functionality for the Ollama project. Here's a summary of the key components:

1. **OllamaConfig**: This struct represents the configuration for a specific LLM (Large Language Model) model, including the model name, prompt prefix and suffix, and whether auto-run is enabled.

2. **Config**: This is the main configuration struct, which includes an array of `OllamaConfig` objects, an `LLMConfig` object, and a flag for auto-saving.

3. **LLMConfig**: This struct represents the configuration for the LLM, including the API token, base URL, model name, maximum tokens, and various parameters like temperature, top-p, presence penalty, and frequency penalty.

4. **LoadConfig()**: This function loads the configuration from a JSON file located at `~/.config/ingest/ingest.json`. If the file does not exist, it creates a default configuration and saves it to the file.

5. **createDefaultConfig()**: This function creates a default configuration and saves it to the specified file path.

6. **getDefaultBaseURL()**: This function returns the default base URL for the LLM API, based on environment variables.

7. **OpenConfig()**: This function opens the configuration file in the default editor, as specified by the `EDITOR` environment variable (or "vim" if not set).

8. **runCommand()**: This is a helper function that runs a command in the shell, using the specified command and arguments.

The main purpose of this code is to provide a way to configure the Ollama project, including the LLM model, prompt, and various parameters. The configuration is stored in a JSON file and can be easily modified by the user.

---

# File: /Users/samm/git/sammcj/ingest/main.go

## Summary:

The provided code is the main.go file for the "ingest" command-line tool. This tool is designed to generate a Markdown-formatted prompt from files and directories, which can then be used as input for a large language model (LLM) or processed in other ways. Here's a summary of the main components and functionality:

1. **Initialization**: The code sets up a Cobra command-line interface, defining various flags and options for the tool. These include options for excluding/including files, generating git diffs, enabling LLM integration, and more.

2. **main() Function**: The `main()` function is the entry point of the application. It calls the `rootCmd.Execute()` function to run the command.

3. **run() Function**: The `run()` function is the main logic of the tool. It performs the following tasks:
   - Processes the provided paths (files or directories) and generates a tree-like representation of the source code.
   - Handles git operations (diffs and logs) for the provided paths.
   - Renders the source code using a custom template.
   - Optionally saves the generated output to a file or the clipboard.
   - Optionally sends the output to an LLM API for inference.
   - Optionally estimates the vRAM requirements for the generated content based on the specified model and quantization settings.

4. **handleOutput() Function**: This function handles the output of the generated prompt, either by printing it to the console, writing it to a file, or copying it to the clipboard.

5. **handleLLMOutput() Function**: This function sends the generated prompt to an LLM API (specifically the OpenAI API) for inference and streams the response back to the console.

6. **performVRAMEstimation() Function**: This function estimates the vRAM requirements for the generated content based on the specified model, quantization, and memory settings.

7. **autoSaveOutput() Function**: This function automatically saves the generated output to a file in the user's home directory (~/ingest/<dirname>.md).

8. **runCompletion() Function**: This function generates shell completion scripts for Bash, Zsh, and Fish.

The tool is highly configurable, allowing users to customize the include/exclude patterns, git operations, output format, and LLM integration. It also provides vRAM estimation capabilities to help users understand the resource requirements of the generated content.

Overall, this code provides a powerful and flexible tool for generating prompts from source code, which can be useful for a variety of applications, such as training or fine-tuning large language models.

---

# File: /Users/samm/git/sammcj/ingest/utils/output_manager.go

## Summary:

This code defines an `OutputMessage` struct and provides functions to manage a queue of output messages. Here's a summary of the main components and functionality:

1. **OutputMessage Struct**: This struct represents a single output message, containing a symbol, the message text, a color attribute, and a priority value.

2. **AddMessage Function**: This function adds a new `OutputMessage` to the queue. It takes the symbol, message, color, and priority as input parameters.

3. **PrintMessages Function**: This function is responsible for printing all the collected messages in the queue. It first sorts the messages by priority (lower priority messages are printed later), then iterates through the sorted messages and prints them using the `PrintColouredMessage` function (which is likely defined elsewhere).

4. **Concurrency Management**: The code uses a `sync.Mutex` to ensure thread-safety when adding and printing messages. This allows the `AddMessage` and `PrintMessages` functions to be called concurrently without race conditions.

The main purpose of this code is to provide a centralized way to manage and display output messages, with the ability to control the order of messages based on their priority. This can be useful in a command-line application or a logging system, where you want to ensure that important messages are displayed prominently, while less critical messages are still available for debugging or informational purposes.

The `utils.go` file likely contains the implementation of the `PrintColouredMessage` function, which is responsible for actually printing the messages with the specified color.

---

