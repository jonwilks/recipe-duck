# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Recipe Duck is a Python CLI tool that converts recipe images into structured markdown files using AI vision capabilities. The tool processes photos or screenshots of recipes and extracts ingredients, instructions, and metadata into a standardized format.

## Architecture

### Core Components

- **`src/recipe_duck/cli.py`**: CLI entry point using Click. Handles argument parsing, file I/O, and user interaction.
- **`src/recipe_duck/processor.py`**: Core processing logic. Contains `RecipeProcessor` class that:
  - Encodes images to base64 for API submission
  - Calls Anthropic's Claude API with vision capabilities
  - Uses a structured prompt template to ensure consistent markdown output
  - Coordinates URL processing and print URL detection
- **`src/recipe_duck/url_extractor.py`**: URL handling and print-friendly version detection:
  - Fetches webpage HTML
  - Implements hybrid print URL detection (pattern matching + LLM fallback)
  - Caches successful patterns by domain
  - Extracts clean text content from HTML
- **`src/recipe_duck/config.py`**: Configuration classes for formatting and print URL detection
- **`src/recipe_duck/formatter.py`**: Post-processing for deterministic formatting
- **`src/recipe_duck/__init__.py`**: Package initialization and version info

### Data Flow

**Image Processing:**
1. User provides image path via CLI
2. CLI validates input and loads API credentials
3. `RecipeProcessor.process_image()` orchestrates:
   - Image loading and encoding (`_encode_image()`)
   - API call with vision model (`_extract_recipe()`)
   - Returns markdown string
4. CLI writes markdown to output file

**URL Processing:**
1. User provides recipe URL via CLI
2. CLI validates input and loads API credentials
3. `RecipeProcessor.process_url()` orchestrates:
   - Print URL detection via `URLRecipeExtractor.find_best_url()`:
     a. Check domain cache for known patterns
     b. Try common print URL patterns (?print, ?printview, /wprm_print/slug, etc.)
     c. If patterns fail, optionally use LLM to analyze HTML for print buttons
     d. Fall back to original URL if nothing works
   - Fetch webpage HTML from best URL
   - Extract clean text content (remove scripts, nav, ads)
   - API call with text extraction model (`_extract_recipe_from_url()`)
   - Returns markdown string
4. CLI writes markdown to output file

### AI Integration

The project uses Anthropic's Claude API with vision models (default: claude-3-5-sonnet-20241022). The `_extract_recipe()` method sends:
- Base64-encoded image
- Structured prompt defining the exact markdown template
- The AI handles both OCR and semantic understanding in a single call

### Output Format

All recipes follow this standardized markdown structure:
```markdown
# [Recipe Name]
**Prep Time:** / **Cook Time:** / **Total Time:** / **Servings:**
## Ingredients
## Instructions
## Notes
```

## Development Commands

### Setup
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Running the tool
```bash
recipe-duck path/to/image.jpg              # Basic usage
recipe-duck image.jpg -o output.md         # Specify output
recipe-duck image.jpg --model claude-3-opus-20240229  # Different model
```

### Testing and Quality
```bash
pytest                    # Run tests
pytest tests/test_foo.py  # Run specific test file
black src/ tests/         # Format code
ruff check src/ tests/    # Lint
mypy src/                 # Type check
```

## Configuration

- API key: Set `ANTHROPIC_API_KEY` environment variable or use `--api-key` flag
- Model selection: Use `--model` flag (see Anthropic docs for available vision models)
- Output format: Controlled by prompt template in `processor.py:_extract_recipe()`

## Key Design Decisions

1. **Single API call**: Vision models handle both OCR and structured extraction, avoiding separate OCR preprocessing
2. **Prompt-based formatting**: Markdown structure enforced via detailed prompt rather than post-processing
3. **CLI-first design**: No web frontend to keep the tool lightweight and scriptable
4. **Minimal image preprocessing**: Relies on Claude's robust image handling; only format conversion if needed
5. **Hybrid print URL detection**: Combines fast pattern matching with intelligent LLM fallback for maximum success rate while minimizing API costs
6. **Domain-level caching**: Remembers successful print URL patterns per domain to avoid repeated detection
7. **Lambda-optimized logging**: Automatically enables verbose logging in AWS Lambda for CloudWatch visibility

## Extending the Project

### Adding new output formats
Modify the prompt template in `processor.py:_extract_recipe()` or add new methods to support multiple format options.

### Supporting batch processing
Add batch mode to CLI that accepts directory input and processes multiple images sequentially.

### Custom recipe templates
Allow users to provide custom markdown templates via config file or CLI flag, replacing the hardcoded prompt.

### Local OCR fallback
Add optional Tesseract integration for users without API access or for preprocessing before API calls.
