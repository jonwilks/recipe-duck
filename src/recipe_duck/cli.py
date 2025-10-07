"""CLI entry point for recipe-duck."""

import click
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from recipe_duck.processor import RecipeProcessor
from recipe_duck.notion_client import NotionRecipeClient

# Load .env file if present
load_dotenv()


@click.command()
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output markdown file path (default: same name as image with .md extension)",
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
def main(
    image_path: Path,
    output: Optional[Path],
    api_key: Optional[str],
    cheap: bool,
    model: Optional[str],
    notion: bool,
    notion_api_key: Optional[str],
    notion_database_id: Optional[str],
    no_format: bool,
    verbose: bool,
) -> None:
    """Convert a recipe image to structured markdown format.

    Takes an image file containing a recipe and uses AI to extract
    ingredients and instructions into a standardized markdown format.
    """
    if not api_key:
        raise click.ClickException(
            "API key required. Set ANTHROPIC_API_KEY environment variable or use --api-key"
        )

    if verbose:
        click.echo(f"📷 Processing recipe image: {image_path}")
        click.echo(f"📁 Image size: {image_path.stat().st_size / 1024:.1f} KB")
    else:
        click.echo(f"Processing recipe image: {image_path}")

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

    processor = RecipeProcessor(
        api_key=api_key,
        model=selected_model,
        apply_formatting=not no_format,
    )

    try:
        if verbose:
            click.echo("🔍 Encoding image...")

        markdown_content = processor.process_image(image_path, verbose=verbose)

        # Save to file if output path provided or notion flag not set
        if output or not notion:
            if output is None:
                output = image_path.with_suffix(".md")

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
