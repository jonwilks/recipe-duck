# Recipe Duck

Convert recipe images to structured markdown using AI, with optional Notion database integration.

## Overview

Recipe Duck analyzes images of recipes (photos or screenshots) and extracts them into a standardized markdown format. It uses Claude's vision capabilities to understand ingredients, instructions, and metadata from recipe images. You can save recipes as markdown files or push them directly to a Notion database.

## Setup

### Prerequisites

- Python 3.11 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))
- (Optional) Notion API key and database ID for Notion integration

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd recipe-duck
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package in editable mode:
```bash
pip install -e .
```

4. Set up your API keys:
```bash
cp .env.example .env
# Edit .env and add your API keys:
# - ANTHROPIC_API_KEY (required)
# - NOTION_API_KEY (optional, for Notion integration)
# - NOTION_DATABASE_ID (optional, for Notion integration)
```

Or export them directly:
```bash
export ANTHROPIC_API_KEY=your_api_key_here
export NOTION_API_KEY=your_notion_key_here
export NOTION_DATABASE_ID=your_database_id_here
```

## Usage

### Markdown Output

Basic usage:
```bash
recipe-duck path/to/recipe-image.jpg
```

This will create `recipe-image.md` in the same directory.

Specify output location:
```bash
recipe-duck recipe.jpg -o my-recipes/chocolate-cake.md
```

Use cheaper AI model (75% cost savings):
```bash
recipe-duck recipe.jpg --cheap
```

Disable deterministic formatting (see [Formatting](#formatting) below):
```bash
recipe-duck recipe.jpg --no-format
```

Enable verbose logging (shows timing, token usage, and costs):
```bash
recipe-duck recipe.jpg -v
```

Combine options:
```bash
recipe-duck recipe.jpg --cheap --notion -v
```

Advanced: Use a specific model (overrides `--cheap`):
```bash
recipe-duck recipe.jpg --model claude-3-opus-20240229
```

### Debugging

Enable debug mode to troubleshoot extraction issues. Debug mode writes detailed files showing exactly what the AI sees and returns:

```bash
# Write debug files to current directory
recipe-duck recipe.jpg --debug

# Write debug files to specific directory (recommended - keeps your workspace clean)
recipe-duck recipe.jpg --debug --debug-dir ./debug

# Works with URLs too
recipe-duck https://example.com/recipe --debug --debug-dir ./debug
```

When using `--debug` with `--debug-dir`, all output files go to the debug directory:

**For image extraction:**
- `debug_prompt_image.txt` - The full prompt sent to Claude, including instructions
- `debug_response_image.txt` - Claude's raw markdown response (before formatting)
- `recipe.md` - The final formatted recipe output

**For URL extraction:**
- `debug_prompt_url.txt` - The full prompt including extracted webpage content (shows exactly what Claude sees from the webpage)
- `debug_response_url.txt` - Claude's raw markdown response (before formatting)
- `recipe_name.md` - The final formatted recipe output

**Note:** If you specify `-o` (output path), that takes precedence over the debug directory.

**When to use debug mode:**
- Missing ingredients or instructions in output
- Incorrect recipe extraction
- Verifying what content was extracted from a webpage
- Understanding how the AI interprets your recipes
- Comparing prompts across different runs

Example workflow:
```bash
# Extract recipe with debug enabled
recipe-duck https://example.com/recipe --debug --debug-dir ./debug -o output.md

# Review the files:
# 1. Check debug/debug_prompt_url.txt to see what webpage content was extracted
# 2. Check debug/debug_response_url.txt to see Claude's raw output
# 3. Compare with output.md (the final formatted version)
```

### URL Processing (Recipe Websites)

Recipe Duck can extract recipes directly from URLs:

```bash
recipe-duck https://www.budgetbytes.com/easy-dumpling-soup/
```

#### Print-Friendly URL Detection

When processing URLs, Recipe Duck automatically tries to find print-friendly versions of recipe pages. Print versions typically remove ads, navigation, popups, and other clutter, resulting in:
- **Better extraction quality** - Cleaner HTML means more reliable recipe parsing
- **Lower token costs** - Less content to process = fewer API tokens used
- **Faster processing** - Smaller pages load and process faster

**How it works:**

Recipe Duck uses a hybrid approach:
1. **Pattern matching** (fast): Tries common print URL patterns like `?print`, `?printview`, `/wprm_print/slug`
2. **Domain caching**: Remembers successful patterns for each website
3. **LLM fallback**: If patterns fail, asks Claude to analyze the page HTML for print buttons
4. **Graceful fallback**: If no print version exists, uses the original URL

**Supported patterns:**
- `?print` - Serious Eats, many food blogs
- `?printview` - Allrecipes
- `/wprm_print/[recipe-slug]` - WordPress Recipe Maker (Budget Bytes, Pinch of Yum, etc.)
- `/print/` or `/print` - Various WordPress themes

**Example verbose output:**
```bash
$ recipe-duck https://www.budgetbytes.com/easy-dumpling-soup/ -v

[PRINT-URL] Starting search for: https://www.budgetbytes.com/easy-dumpling-soup/
[PRINT-URL] Trying pattern 1/5: https://www.budgetbytes.com/easy-dumpling-soup?print
[PRINT-URL] Trying pattern 2/5: https://www.budgetbytes.com/easy-dumpling-soup?printview
[PRINT-URL] Trying pattern 3/5: https://www.budgetbytes.com/wprm_print/easy-dumpling-soup
[PRINT-URL] ✓ Pattern match! | Method: pattern | Time: 0.34s
[PRINT-URL] Using: https://www.budgetbytes.com/wprm_print/easy-dumpling-soup
```

**Configuration:**

Disable print URL detection:
```bash
recipe-duck https://example.com/recipe --no-print-prefer
```

Use a different model for LLM-based detection:
```bash
recipe-duck https://example.com/recipe --print-detection-model claude-3-haiku-20240307
```

Environment variables (useful for Lambda deployments):
```bash
export RECIPE_DUCK_ENABLE_PRINT_SEARCH=false      # Disable feature
export RECIPE_DUCK_PRINT_DETECTION_MODEL=claude-3-5-haiku-20241022  # Detection model
export RECIPE_DUCK_PRINT_SEARCH_TIMEOUT=15        # Timeout budget in seconds
```

**Lambda/CloudWatch logging:**

When running in AWS Lambda (detected via `AWS_LAMBDA_FUNCTION_NAME` environment variable), verbose logging is automatically enabled. All print URL detection steps will appear in CloudWatch logs with `[PRINT-URL]` prefixes for easy filtering.

### Notion Integration

Push recipe directly to Notion database:
```bash
recipe-duck recipe.jpg --notion
```

This will:
1. Extract the recipe from the image using AI
2. Create a new page in your Notion database with the recipe name as the title
3. Add ingredients, instructions, and notes as page content

You can also save to markdown AND push to Notion:
```bash
recipe-duck recipe.jpg -o my-recipe.md --notion
```

#### Setting up Notion

1. Create a Notion integration at https://www.notion.so/my-integrations
2. Copy the API key (starts with `ntn_`)
3. Create or select a database for recipes
4. Share the database with your integration
5. Copy the database ID from the URL (the part before `?v=`)
6. Add both to your `.env` file

## Development

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```

Format code:
```bash
black src/ tests/
```

Lint:
```bash
ruff check src/ tests/
```

Type check:
```bash
mypy src/
```

## Output Format

The tool generates markdown in this format:

```markdown
# [Recipe Name]

**Prep Time:** [time]
**Cook Time:** [time]
**Total Time:** [time]
**Servings:** [number]

## Ingredients

- [ingredient with amount]
- [ingredient with amount]

## Instructions

1. [First instruction step]
2. [Second instruction step]

## Notes

- [Any additional notes, tips, or variations]
```

## Formatting

Recipe Duck applies **deterministic formatting** by default to ensure consistency across all extracted recipes:

### What Gets Normalized

- **Units**: Abbreviated units are expanded to their full form
  - `tbsp` → `tablespoon`, `tsp` → `teaspoon`
  - `oz` → `ounce`, `lb` → `pound`
  - `c` → `cup`, `pt` → `pint`, `qt` → `quart`

- **Fractions**: Unicode and decimal fractions are converted to ASCII
  - `½` → `1/2`, `¼` → `1/4`, `¾` → `3/4`
  - `0.5` → `1/2`, `0.25` → `1/4`

- **Pluralization**: Units are automatically pluralized based on quantity
  - `2 tablespoon` → `2 tablespoons`
  - `1 cup` → `1 cup` (singular)

- **Numbered steps**: Instructions are always sequentially numbered (1., 2., 3., etc.)

- **Bullet points**: Ingredients are always formatted with consistent bullet points (-)

### Why Deterministic Formatting?

This approach ensures:
- **Consistency**: All recipes follow the same format regardless of source image style
- **Searchability**: Standardized units and fractions make recipes easier to search
- **Reliability**: No variation in output formatting between runs
- **Portability**: Clean ASCII fractions work everywhere (unlike unicode characters)

### Customization

The formatting rules are defined in `src/recipe_duck/config.py` with sensible defaults. You can:

1. **Disable formatting** entirely with the `--no-format` flag:
   ```bash
   recipe-duck recipe.jpg --no-format
   ```

2. **Customize rules** programmatically by providing a custom `FormattingConfig`:
   ```python
   from recipe_duck.config import FormattingConfig
   from recipe_duck.processor import RecipeProcessor

   custom_config = FormattingConfig(
       unit_normalizations={"T": "tablespoon", "t": "teaspoon"},
       pluralize_units=False,
   )

   processor = RecipeProcessor(
       api_key="your-key",
       formatting_config=custom_config
   )
   ```

3. **Edit defaults** in `src/recipe_duck/config.py` to change project-wide behavior

## License

MIT
