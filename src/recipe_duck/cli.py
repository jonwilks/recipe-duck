"""CLI entry point for recipe-duck."""

import click
from pathlib import Path
from typing import Optional

from recipe_duck.processor import RecipeProcessor


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
    "--model",
    default="claude-3-5-sonnet-20241022",
    help="Claude model to use",
)
def main(
    image_path: Path,
    output: Optional[Path],
    api_key: Optional[str],
    model: str,
) -> None:
    """Convert a recipe image to structured markdown format.

    Takes an image file containing a recipe and uses AI to extract
    ingredients and instructions into a standardized markdown format.
    """
    if not api_key:
        raise click.ClickException(
            "API key required. Set ANTHROPIC_API_KEY environment variable or use --api-key"
        )

    # Default output path
    if output is None:
        output = image_path.with_suffix(".md")

    click.echo(f"Processing recipe image: {image_path}")

    processor = RecipeProcessor(api_key=api_key, model=model)

    try:
        markdown_content = processor.process_image(image_path)
        output.write_text(markdown_content)
        click.echo(f"✓ Recipe saved to: {output}")
    except Exception as e:
        raise click.ClickException(f"Failed to process recipe: {e}")


if __name__ == "__main__":
    main()
