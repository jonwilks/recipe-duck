"""CLI entry point for recipe-duck."""

import re
import click
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

from recipe_duck.processor import RecipeProcessor
from recipe_duck.notion_client import NotionRecipeClient

# Load .env file if present
load_dotenv()


def is_url(input_str: str) -> bool:
    """Check if input string is a URL.

    Args:
        input_str: Input string to check

    Returns:
        True if input is a URL, False otherwise
    """
    return input_str.startswith(("http://", "https://"))


def generate_filename_from_url(url: str) -> str:
    """Generate a filename from a URL.

    Args:
        url: URL to parse

    Returns:
        Filename string (without extension)
    """
    parsed = urlparse(url)

    # Extract meaningful name from URL path
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    filename = "recipe"  # default

    # Find best part of URL for filename (prefer later parts, skip numbers)
    for part in reversed(path_parts):
        if len(part) > 3 and not part.isdigit():
            filename = part.replace("-", "_").replace(" ", "_")
            break

    # Clean filename - remove special chars
    filename = re.sub(r"[^\w\-_]", "_", filename)
    filename = re.sub(r"[_-]+", "_", filename).strip("_")

    return filename


@click.command()
@click.argument("input_path", type=str)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output markdown file path (default: same name as input with .md extension)",
)
@click.option(
    "--api-key",
    envvar="ANTHROPIC_API_KEY",
    help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
)
@click.option(
    "--cheap",
    is_flag=True,
    help="Use cheaper AI model (75%% cost savings, slightly lower quality)",
)
@click.option(
    "--model",
    default=None,
    help="Claude model to use (overrides --cheap flag)",
)
@click.option(
    "--notion",
    is_flag=True,
    help="Push recipe to Notion database (requires NOTION_API_KEY and NOTION_DATABASE_ID env vars)",
)
@click.option(
    "--notion-api-key",
    envvar="NOTION_API_KEY",
    help="Notion API key (or set NOTION_API_KEY env var)",
)
@click.option(
    "--notion-database-id",
    envvar="NOTION_DATABASE_ID",
    help="Notion database ID (or set NOTION_DATABASE_ID env var)",
)
@click.option(
    "--no-format",
    is_flag=True,
    help="Disable deterministic formatting (units, fractions, numbering)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode (shows full prompts and API responses)",
)
@click.option(
    "--debug-dir",
    type=click.Path(path_type=Path),
    help="Directory to write debug files (default: current directory)",
)
def main(
    input_path: str,
    output: Optional[Path],
    api_key: Optional[str],
    cheap: bool,
    model: Optional[str],
    notion: bool,
    notion_api_key: Optional[str],
    notion_database_id: Optional[str],
    no_format: bool,
    verbose: bool,
    debug: bool,
    debug_dir: Optional[Path],
) -> None:
    """Convert a recipe image or URL to structured markdown format.

    Takes an image file or URL containing a recipe and uses AI to extract
    ingredients and instructions into a standardized markdown format.
    """
    if not api_key:
        raise click.ClickException(
            "API key required. Set ANTHROPIC_API_KEY environment variable or use --api-key"
        )

    # Detect if input is a URL or file path
    input_is_url = is_url(input_path)

    # Validate input
    if not input_is_url:
        # Check if file exists
        file_path = Path(input_path)
        if not file_path.exists():
            raise click.ClickException(f"File not found: {input_path}")

        if verbose:
            click.echo(f"📷 Processing recipe image: {input_path}")
            click.echo(f"📁 Image size: {file_path.stat().st_size / 1024:.1f} KB")
        else:
            click.echo(f"Processing recipe image: {input_path}")
    else:
        if verbose:
            click.echo(f"🌐 Processing recipe from URL: {input_path}")
        else:
            click.echo(f"Processing recipe from URL: {input_path}")

    # Determine which model to use
    if model:
        # Explicit model overrides everything
        selected_model = model
        if verbose:
            click.echo(f"🤖 Using custom model: {selected_model}")
    elif cheap:
        # Use cheap model (Haiku)
        selected_model = "claude-3-5-haiku-20241022"
        if verbose:
            click.echo(f"💰 Using cheap model: {selected_model}")
    else:
        # Default to Sonnet
        selected_model = "claude-3-5-sonnet-20241022"
        if verbose:
            click.echo(f"🤖 Using default model: {selected_model}")

    if verbose:
        click.echo(f"✨ Formatting enabled: {not no_format}")

    # Validate and create debug directory if needed
    if debug and debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        if verbose:
            click.echo(f"📁 Debug files will be written to: {debug_dir}")

    processor = RecipeProcessor(
        api_key=api_key,
        model=selected_model,
        apply_formatting=not no_format,
    )

    try:
        if not input_is_url and verbose:
            click.echo("🔍 Encoding image...")

        # Use unified process method
        markdown_content = processor.process(input_path, verbose=verbose, debug=debug, debug_dir=debug_dir)

        # Save to file if output path provided or notion flag not set
        if output or not notion:
            if output is None:
                # Generate output filename based on input type
                if input_is_url:
                    filename = generate_filename_from_url(input_path)
                    base_filename = f"{filename}.md"
                else:
                    base_filename = Path(input_path).with_suffix(".md").name

                # If debug mode is enabled and debug_dir is set, put output in debug_dir
                if debug and debug_dir:
                    output = debug_dir / base_filename
                else:
                    output = Path(base_filename)

            if verbose:
                click.echo(f"💾 Writing markdown to: {output}")
                click.echo(f"📝 Content size: {len(markdown_content)} characters")

            output.write_text(markdown_content)
            click.echo(f"✓ Recipe saved to: {output}")

        # Push to Notion if requested
        if notion:
            if not notion_api_key or not notion_database_id:
                raise click.ClickException(
                    "Notion integration requires --notion-api-key and --notion-database-id "
                    "(or NOTION_API_KEY and NOTION_DATABASE_ID env vars)"
                )

            if verbose:
                click.echo(f"📤 Pushing recipe to Notion...")
                click.echo(f"🔑 Database ID: {notion_database_id[:8]}...")
            else:
                click.echo("Pushing recipe to Notion...")

            notion_client = NotionRecipeClient(
                api_key=notion_api_key,
                database_id=notion_database_id
            )
            page_url = notion_client.push_recipe(markdown_content, verbose=verbose)
            click.echo(f"✓ Recipe added to Notion: {page_url}")

    except Exception as e:
        raise click.ClickException(f"Failed to process recipe: {e}")


if __name__ == "__main__":
    main()
