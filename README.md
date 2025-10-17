# Recipe Duck

Convert recipe images, URLs, and YouTube videos to structured markdown using AI, with optional Notion database integration.

## Overview

Recipe Duck extracts recipes from multiple sources and converts them into a standardized markdown format:
- **Images** - Photos or screenshots of recipes using Claude's vision capabilities
- **Recipe URLs** - Web pages from recipe sites (auto-detects print-friendly versions)
- **YouTube Videos** - Extracts recipes from video description boxes

You can save recipes as markdown files or push them directly to a Notion database.

**Two ways to use Recipe Duck:**
- **CLI Tool** - Run locally from the command line
- **Cloud Deployment** - Send recipes via email, automatically processed and added to Notion ([deployment guide](docs/DEPLOYMENT.md))

## Setup

### CLI Tool Setup

#### Prerequisites

- Python 3.11 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))
- (Optional) YouTube Data API v3 key for YouTube support (falls back to web scraping if not provided)
- (Optional) Notion API key and database ID for Notion integration

#### Installation

```bash
# Clone and install
git clone <repository-url>
cd recipe-duck
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .

# Set up API keys
export ANTHROPIC_API_KEY=your_api_key_here
export YOUTUBE_API_KEY=your_youtube_key_here  # Optional, for YouTube API access
export NOTION_API_KEY=your_notion_key_here  # Optional, for Notion integration
export NOTION_DATABASE_ID=your_database_id_here  # Optional, for Notion integration
```

### Cloud Deployment Setup

Deploy Recipe Duck to AWS Lambda for email-based recipe processing. See **[terraform/README.md](terraform/README.md)** and **[lambda/README.md](lambda/README.md)** for setup details.

**Features:** Email recipes → Auto-process → Add to Notion. HEIC support, email whitelist, ~$1-2/month.

## Usage

### Basic Usage

```bash
# Process an image
recipe-duck recipe.jpg

# Process a recipe URL
recipe-duck https://www.budgetbytes.com/easy-dumpling-soup/

# Process a YouTube video (extracts from description box)
recipe-duck https://www.youtube.com/watch?v=VIDEO_ID

# Specify output location
recipe-duck recipe.jpg -o my-recipes/chocolate-cake.md

# Push to Notion
recipe-duck recipe.jpg --notion

# Use cheaper model (Haiku 3.5 instead of default Haiku 4.5)
recipe-duck recipe.jpg --cheap

# Enable verbose logging
recipe-duck recipe.jpg -v

# Combine options
recipe-duck https://www.youtube.com/watch?v=VIDEO_ID --cheap --notion -v
```

**Default Model:** Claude Haiku 4.5 (excellent quality, 1/3 cost and 2x+ speed of Sonnet)

### Debugging

```bash
# Enable debug mode to see prompts and raw AI responses
recipe-duck recipe.jpg --debug --debug-dir ./debug
```

Creates `debug_prompt_*.txt`, `debug_response_*.txt`, and final output for troubleshooting extraction issues.

### URL Processing

#### Recipe Websites

Recipe Duck automatically finds print-friendly versions of recipe pages (cleaner HTML, lower costs, better extraction). Uses pattern matching (`?print`, `?printview`, `/wprm_print/slug`), domain caching, and optional LLM fallback.

**Disable:** `--no-print-prefer` | **Configure:** `RECIPE_DUCK_ENABLE_PRINT_SEARCH`, `RECIPE_DUCK_PRINT_DETECTION_MODEL`

#### YouTube Videos

Extract recipes from YouTube video description boxes. Supports multiple URL formats (`youtube.com/watch?v=`, `youtu.be/`, etc.).

```bash
# With YouTube API key (recommended for reliability)
recipe-duck https://www.youtube.com/watch?v=VIDEO_ID --youtube-api-key YOUR_KEY

# Without API key (uses web scraping fallback)
recipe-duck https://www.youtube.com/watch?v=VIDEO_ID
```

**YouTube API Setup:** Get a free API key at [Google Cloud Console](https://console.cloud.google.com/) → Enable YouTube Data API v3 → Create credentials. Free tier: 10,000 units/day (1 unit per video).

### Notion Integration

```bash
recipe-duck recipe.jpg --notion
```

**Setup:** Create integration at https://www.notion.so/my-integrations, share database, add `NOTION_API_KEY` and `NOTION_DATABASE_ID` to env.

**Recommended Properties:** Name (title), Cuisine (multi-select), Protein (multi-select), Course (multi-select), Method (multi-select), Effort (select: 🔪/🔪🔪/🔪🔪🔪), Rating (select)

## Development

```bash
pip install -e ".[dev]"  # Install dev dependencies
pytest                    # Run tests
black src/ tests/         # Format
ruff check src/ tests/    # Lint
mypy src/                 # Type check
```

## Output Format

Recipes are structured with:
- **Properties:** Cuisine, Protein, Course, Method, Effort, Rating, Cook Time
- **Ingredients:** 3-column tables (Ingredient | Measurement | Method) with optional subheadings for multi-component recipes
- **Directions:** Numbered steps with optional subheadings for multi-phase recipes
- **Sections:** Notes, Links, Nutrition, Photos

**Units:** US Customary (cups, tablespoons, ounces, etc.)

## Formatting

Applies deterministic formatting for consistency: expands abbreviated units (`tbsp` → `tablespoon`), converts fractions to ASCII (`½` → `1/2`), auto-pluralizes units, numbers steps sequentially.

**Disable:** `--no-format` | **Customize:** Edit `src/recipe_duck/config.py` or pass custom `FormattingConfig`

## License

MIT
