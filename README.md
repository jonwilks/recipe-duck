# Recipe Duck 🦆

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
