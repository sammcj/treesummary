package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/gob"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
	"github.com/schollz/progressbar/v3"
)

type Config struct {
	AWSRegion             string   `json:"aws_region"`
	AnthropicVersion      string   `json:"anthropic_version"`
	FileExtensions        []string `json:"file_extensions"`
	SystemPrompt          string   `json:"system_prompt"`
	FilePrompt            string   `json:"file_prompt"`
	SummaryPrompt         string   `json:"summary_prompt"`
	FinalSummaryMaxTokens int      `json:"final_summary_max_tokens"`
	FinalSummaryPrompt    string   `json:"final_summary_prompt"`
	GenerateFinalSummary  bool     `json:"generate_final_summary"`
	IgnorePaths           []string `json:"ignore_paths"`
	Limit                 int      `json:"limit"`
	MaxTokens             int      `json:"max_tokens"`
	ModelID               string   `json:"model_id"`
	Parallel              int      `json:"parallel"`
	SupersummaryInterval  int      `json:"supersummary_interval"`
	Temperature           float64  `json:"temperature"`
	TopP                  float64  `json:"top_p"`
	Verbose               bool     `json:"verbose"`
}

type State struct {
	ProcessedFiles map[string]bool
	LastDirectory  string
}

func loadState(stateFile string) State {
	state := State{ProcessedFiles: make(map[string]bool)}
	file, err := os.Open(stateFile)
	if err != nil {
		return state
	}
	defer file.Close()

	decoder := gob.NewDecoder(file)
	err = decoder.Decode(&state)
	if err != nil {
		log.Printf("Error decoding state: %v", err)
	}
	return state
}

func saveState(stateFile string, state State) {
	file, err := os.Create(stateFile)
	if err != nil {
		log.Printf("Error creating state file: %v", err)
		return
	}
	defer file.Close()

	encoder := gob.NewEncoder(file)
	err = encoder.Encode(state)
	if err != nil {
		log.Printf("Error encoding state: %v", err)
	}
}

func getDirectoryTree(path string, maxDepth int, ignorePaths []string) string {
	var tree []string
	filepath.Walk(path, func(filePath string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		level := strings.Count(filePath[len(path):], string(os.PathSeparator))
		if level > maxDepth {
			return filepath.SkipDir
		}
		for _, ignorePath := range ignorePaths {
			if strings.Contains(filePath, ignorePath) {
				if info.IsDir() {
					return filepath.SkipDir
				}
				return nil
			}
		}
		indent := strings.Repeat("  ", level)
		if info.IsDir() {
			tree = append(tree, fmt.Sprintf("%s%s/", indent, info.Name()))
		} else {
			tree = append(tree, fmt.Sprintf("%s%s", indent, info.Name()))
		}
		return nil
	})
	return strings.Join(tree, "\n")
}

func getFilesToProcess(directory string, fileExtensions, ignorePaths []string) []string {
	var filesToProcess []string
	filepath.Walk(directory, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		for _, ignorePath := range ignorePaths {
			if strings.Contains(path, ignorePath) {
				if info.IsDir() {
					return filepath.SkipDir
				}
				return nil
			}
		}
		for _, ext := range fileExtensions {
			if strings.HasSuffix(info.Name(), ext) {
				filesToProcess = append(filesToProcess, path)
				break
			}
		}
		return nil
	})
	return filesToProcess
}

func runIngest(files []string) int {
	if len(files) == 0 {
		fmt.Println("No files to process. Skipping ingestion.")
		return 0
	}

	_, err := exec.LookPath("ingest")
	if err != nil {
		fmt.Println("The 'ingest' command is not available in the system path. Skipping ingestion. (Tip: You can install ingest by running `go install github.com/sammcj/ingest@HEAD`)")
		return 0
	}

	fmt.Printf("Attempting to run ingest on %d files.\n", len(files))
	cmd := exec.Command("ingest", files...)
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = os.Stderr

	err = cmd.Run()
	if err != nil {
		fmt.Printf("Error running ingest command: %v\n", err)
		return 0
	}

	fmt.Println("Ingest command output:")
	fmt.Println(out.String())

	scanner := bufio.NewScanner(&out)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.Contains(line, "Tokens (Approximate): ") {
			var tokenCountStr string
			_, err := fmt.Sscanf(line, "Tokens (Approximate): %s", &tokenCountStr)
			if err == nil {
				fmt.Printf("Extracted token count: %s\n", tokenCountStr)
				// Convert token count to integer (e.g. 4,324 -> 4324)
				tokenCount, _ := strconv.Atoi(strings.ReplaceAll(tokenCountStr, ",", ""))
				return tokenCount
			}
		}
	}
	return 0
}

func summarizeFile(filePath string, client *bedrockruntime.Client, cfg Config, projectTree string) (string, error) {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return "", err
	}

	directory := filepath.Dir(filePath)
	filesInDirectory, err := os.ReadDir(directory)
	if err != nil {
		return "", err
	}

	var fileNames []string
	for _, file := range filesInDirectory {
		if !file.IsDir() {
			fileNames = append(fileNames, file.Name())
		}
	}

	promptContext := fmt.Sprintf(`
Project Structure:
%s

Files in the same directory as %s:
%s

File Content:
%s
	`, projectTree, filepath.Base(filePath), strings.Join(fileNames, ", "), string(content))

	messages := []map[string]interface{}{
		{
			"role":    "user",
			"content": fmt.Sprintf("%s\n\n%s\n\n%s", cfg.SystemPrompt, cfg.FilePrompt, promptContext),
		},
	}

	payload, err := json.Marshal(map[string]interface{}{
		"anthropic_version": "bedrock-2023-05-31",
		"max_tokens":        cfg.MaxTokens,
		"messages":          messages,
		"temperature":       cfg.Temperature,
		"top_p":             cfg.TopP,
	})
	if err != nil {
		return "", err
	}

	output, err := client.InvokeModel(context.Background(), &bedrockruntime.InvokeModelInput{
		ModelId:     aws.String(cfg.ModelID),
		ContentType: aws.String("application/json"),
		Body:        payload,
	})
	if err != nil {
		return "", err
	}

	var response struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
	}
	err = json.Unmarshal(output.Body, &response)
	if err != nil {
		return "", fmt.Errorf("failed to unmarshal response: %v", err)
	}

	if len(response.Content) == 0 || response.Content[0].Text == "" {
		return "", fmt.Errorf("unexpected response format: content is missing or empty")
	}

	return response.Content[0].Text, nil
}

func summarizeSummaries(summaries map[string]string, client *bedrockruntime.Client, cfg Config) (string, error) {
	var promptContext strings.Builder
	for file, summary := range summaries {
		fmt.Fprintf(&promptContext, "File: %s\nSummary: %s\n\n", file, summary)
	}

	messages := []map[string]interface{}{
		{
			"role":    "user",
			"content": fmt.Sprintf("%s\n\n%s\n\n%s", cfg.SystemPrompt, cfg.SummaryPrompt, promptContext.String()),
		},
	}

	payload, err := json.Marshal(map[string]interface{}{
		"anthropic_version": "bedrock-2023-05-31",
		"max_tokens":        cfg.MaxTokens,
		"messages":          messages,
		"temperature":       cfg.Temperature,
		"top_p":             cfg.TopP,
	})
	if err != nil {
		return "", err
	}

	output, err := client.InvokeModel(context.Background(), &bedrockruntime.InvokeModelInput{
		ModelId:     aws.String(cfg.ModelID),
		ContentType: aws.String("application/json"),
		Body:        payload,
	})
	if err != nil {
		return "", err
	}

	var response struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
	}
	err = json.Unmarshal(output.Body, &response)
	if err != nil {
		return "", fmt.Errorf("failed to unmarshal response: %v", err)
	}

	if len(response.Content) == 0 || response.Content[0].Text == "" {
		return "", fmt.Errorf("unexpected response format: content is missing or empty")
	}

	return response.Content[0].Text, nil
}
func processBatch(files []string, client *bedrockruntime.Client, config Config, stateFile string, projectTree string) map[string]string {
	fmt.Printf("Processing batch of %d files.\n", len(files))
	summaries := make(map[string]string)
	var mutex sync.Mutex
	var wg sync.WaitGroup

	bar := progressbar.Default(int64(len(files)))

	for _, filePath := range files {
		wg.Add(1)
		go func(filePath string) {
			defer wg.Done()
			summary, err := summarizeFile(filePath, client, config, projectTree)
			if err != nil {
				log.Printf("Error processing file %s: %v", filePath, err)
				return
			}
			mutex.Lock()
			summaries[filePath] = summary
			state := loadState(stateFile)
			state.ProcessedFiles[filePath] = true
			saveState(stateFile, state)
			mutex.Unlock()
			bar.Add(1)
		}(filePath)
	}

	wg.Wait()
	return summaries
}

func saveToMarkdown(results map[string]string, outputFile string) error {
	file, err := os.Create(outputFile)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := bufio.NewWriter(file)
	for filePath, summary := range results {
		safeFilePath := strings.ReplaceAll(filePath, "#", "\\#")
		fmt.Fprintf(writer, "# File: %s\n\n## Summary:\n\n", safeFilePath)

		lines := strings.Split(summary, "\n")
		inCodeBlock := false
		for _, line := range lines {
			if strings.HasPrefix(strings.TrimSpace(line), "```") {
				inCodeBlock = !inCodeBlock
				fmt.Fprintln(writer, line)
			} else if inCodeBlock {
				fmt.Fprintln(writer, line)
			} else {
				if strings.HasPrefix(strings.TrimSpace(line), "- ") || strings.HasPrefix(strings.TrimSpace(line), "* ") || strings.HasPrefix(strings.TrimSpace(line), "1. ") {
					fmt.Fprintln(writer, "\n"+line)
				} else {
					fmt.Fprintln(writer, line)
				}
			}
		}
		fmt.Fprintln(writer, "---")
	}
	return writer.Flush()
}
func generateFinalSummary(supersummaries []string, client *bedrockruntime.Client, cfg Config) (string, error) {
	var promptContext strings.Builder
	for i, summary := range supersummaries {
		fmt.Fprintf(&promptContext, "Supersummary %d:\n%s\n\n", i+1, summary)
	}

	messages := []map[string]interface{}{
		{
			"role":    "user",
			"content": fmt.Sprintf("%s\n\n%s\n\n%s", cfg.SystemPrompt, cfg.FinalSummaryPrompt, promptContext.String()),
		},
	}

	payload, err := json.Marshal(map[string]interface{}{
		"anthropic_version": cfg.AnthropicVersion,
		"max_tokens":        cfg.FinalSummaryMaxTokens,
		"messages":          messages,
		"temperature":       cfg.Temperature,
		"top_p":             cfg.TopP,
	})
	if err != nil {
		return "", err
	}

	output, err := client.InvokeModel(context.Background(), &bedrockruntime.InvokeModelInput{
		ModelId:     aws.String(cfg.ModelID),
		ContentType: aws.String("application/json"),
		Body:        payload,
	})
	if err != nil {
		return "", err
	}

	// Log the raw response body
	// log.Printf("Debug: Raw API Response Body: %s", string(output.Body))

	var response struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
	}
	err = json.Unmarshal(output.Body, &response)
	if err != nil {
		return "", fmt.Errorf("failed to unmarshal response: %v", err)
	}

	// Log the entire response structure
	// log.Printf("Debug: Parsed API Response Structure: %+v", response)

	if len(response.Content) == 0 || response.Content[0].Text == "" {
		return "", fmt.Errorf("unexpected response format: content is missing or empty")
	}

	return response.Content[0].Text, nil
}

func main() {
	configPath := flag.String("config", "config.json", "Path to the configuration file")
	clearState := flag.Bool("clear-state", false, "Clear the state and restart processing")
	restart := flag.Bool("restart", false, "Restart processing from the beginning")
	flag.Parse()

	if flag.NArg() < 1 {
		log.Fatal("Please provide the directory path as an argument")
	}
	directory := flag.Arg(0)

	configFile, err := os.Open(*configPath)
	if err != nil {
		log.Fatalf("Error opening config file: %v", err)
	}
	defer configFile.Close()

	var cfg Config
	decoder := json.NewDecoder(configFile)
	err = decoder.Decode(&cfg)
	if err != nil {
		log.Fatalf("Error decoding config file: %v", err)
	}

	// Load the AWS SDK configuration
	awsCfg, err := config.LoadDefaultConfig(context.Background(),
		config.WithRegion(cfg.AWSRegion))
	if err != nil {
		log.Fatalf("Unable to load SDK config: %v", err)
	}

	// Create Bedrock Runtime client
	client := bedrockruntime.NewFromConfig(awsCfg)

	timestamp := time.Now().Format("20060102-1504")
	outputDir := filepath.Join(".", "output")
	err = os.MkdirAll(outputDir, 0755)
	if err != nil {
		log.Fatalf("Error creating output directory: %v", err)
	}

	outputFile := filepath.Join(outputDir, fmt.Sprintf("summary_output_%s.md", timestamp))
	supersummaryFile := filepath.Join(outputDir, fmt.Sprintf("supersummary_%s.md", timestamp))
	finalSummaryFile := filepath.Join(outputDir, fmt.Sprintf("final_summary_%s.md", timestamp))
	stateFile := filepath.Join(outputDir, "treesummary_state.gob")

	if *restart || *clearState {
		err = os.Remove(stateFile)
		if err != nil && !os.IsNotExist(err) {
			log.Fatalf("Error clearing state file: %v", err)
		}
		fmt.Println("State file cleared.")
	}

	allFiles := getFilesToProcess(directory, cfg.FileExtensions, cfg.IgnorePaths)
	totalFiles := len(allFiles)
	fmt.Printf("Total files found to process: %d\n", totalFiles)

	var filesToProcess []string
	var state State

	if !*restart && fileExists(stateFile) {
		state = loadState(stateFile)
		filesToProcess = make([]string, 0, totalFiles)
		for _, file := range allFiles {
			if !state.ProcessedFiles[file] {
				filesToProcess = append(filesToProcess, file)
			}
		}
		fmt.Printf("Resuming processing. %d files already processed. %d files remaining.\n", len(state.ProcessedFiles), len(filesToProcess))
	} else {
		filesToProcess = allFiles
		state = State{ProcessedFiles: make(map[string]bool)}
		fmt.Printf("Starting fresh processing of %d files.\n", len(filesToProcess))
	}

	projectTree := getDirectoryTree(directory, 3, cfg.IgnorePaths)
	var supersummaries []string

	for len(filesToProcess) > 0 {
		var batch []string
		if cfg.Limit > 0 && len(filesToProcess) > cfg.Limit {
			batch = filesToProcess[:cfg.Limit]
			filesToProcess = filesToProcess[cfg.Limit:]
		} else {
			batch = filesToProcess
			filesToProcess = nil
		}

		fmt.Printf("Processing batch of %d files.\n", len(batch))
		estimatedTokens := runIngest(batch)
		if estimatedTokens > 0 {
			fmt.Printf("Estimated total tokens for this batch: %d\n", estimatedTokens)
		}

		summaries := processBatch(batch, client, cfg, stateFile, projectTree)
		err = saveToMarkdown(summaries, outputFile)
		if err != nil {
			log.Printf("Error saving to markdown: %v", err)
		} else {
			fmt.Printf("Results have been saved to %s\n", outputFile)
		}

		if cfg.SupersummaryInterval > 0 && len(summaries)%cfg.SupersummaryInterval == 0 {
			fmt.Println("Generating supersummary...")
			supersummary, err := summarizeSummaries(summaries, client, cfg)
			if err != nil {
				log.Printf("Error generating supersummary: %v", err)
			} else {
				supersummaries = append(supersummaries, supersummary)
				err = appendToFile(supersummaryFile, fmt.Sprintf("# Supersummary\n\n%s\n\n---\n\n", supersummary))
				if err != nil {
					log.Printf("Error appending supersummary to file: %v", err)
				} else {
					fmt.Printf("Supersummary has been appended to %s\n", supersummaryFile)
				}
			}
		}

		if len(filesToProcess) > 0 && cfg.Limit > 0 {
			fmt.Printf("Processed %d files. Continue for another batch? (y/n): ", len(batch))
			var answer string
			fmt.Scanln(&answer)
			if strings.ToLower(answer) != "y" {
				break
			}
		}
	}

	state = loadState(stateFile)
	fmt.Printf("Total files processed: %d\n", len(state.ProcessedFiles))

	if cfg.GenerateFinalSummary {
		fmt.Println("Generating final summary...")
		finalSummary, err := generateFinalSummary(supersummaries, client, cfg)
		if err != nil {
			log.Printf("Error generating final summary: %v", err)
		} else {
			err = os.WriteFile(finalSummaryFile, []byte(fmt.Sprintf("# Final Summary\n\n%s", finalSummary)), 0644)
			if err != nil {
				log.Printf("Error saving final summary: %v", err)
			} else {
				fmt.Printf("Final summary has been saved to %s\n", finalSummaryFile)
			}
		}
	}
}

func fileExists(filename string) bool {
	_, err := os.Stat(filename)
	return !os.IsNotExist(err)
}

func appendToFile(filename, content string) error {
	f, err := os.OpenFile(filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = f.WriteString(content)
	return err
}
