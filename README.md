# Recipe Duck 🦆

Convert recipe images to structured markdown using AI.

## Overview

Recipe Duck analyzes images of recipes (photos or screenshots) and extracts them into a standardized markdown format. It uses Claude's vision capabilities to understand ingredients, instructions, and metadata from recipe images.

## Setup

### Prerequisites

- Python 3.11 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))

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

4. Set up your API key:
```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

Or export it directly:
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

Basic usage:
```bash
recipe-duck path/to/recipe-image.jpg
```

This will create `recipe-image.md` in the same directory.

Specify output location:
```bash
recipe-duck recipe.jpg -o my-recipes/chocolate-cake.md
```

Use a different model:
```bash
recipe-duck recipe.jpg --model claude-3-opus-20240229
```

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

## License

MIT
