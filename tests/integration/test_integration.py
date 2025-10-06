"""Integration tests for recipe-duck CLI."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
TEST_IMAGE = FIXTURES_DIR / "cookie-recipe-test.jpeg"


@pytest.fixture
def api_key():
    """Get API key from environment or skip test."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return key


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_cli_basic_usage(api_key, temp_output_dir):
    """Test basic CLI usage: process image and create markdown file."""
    output_file = temp_output_dir / "recipe.md"

    # Run CLI command
    result = subprocess.run(
        [
            "venv/bin/recipe-duck",
            str(TEST_IMAGE),
            "-o",
            str(output_file),
            "--api-key",
            api_key,
        ],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )

    # Check command succeeded
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Check output file was created
    assert output_file.exists(), "Output markdown file was not created"

    # Read output
    content = output_file.read_text()

    # Save recipe to tests/output with title-based filename
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Extract title from first line (remove leading # and strip whitespace)
    first_line = next((line for line in content.split("\n") if line.strip().startswith("#")), "")
    title = first_line.lstrip("#").strip()

    # Create filename from title: lowercase, replace spaces with dashes, remove special chars
    import re
    filename = re.sub(r'[^\w\s-]', '', title.lower())
    filename = re.sub(r'[-\s]+', '-', filename)
    filename = f"{filename}.md"

    recipe_output_path = output_dir / filename
    recipe_output_path.write_text(content)

    print("\n=== Generated Recipe ===")
    print(content)
    print("========================\n")
    print(f"Recipe saved to: {recipe_output_path}")


def test_cli_default_output_path(api_key, temp_output_dir):
    """Test that CLI creates output file with default naming (same as input with .md extension)."""
    # Copy test image to temp dir
    temp_image = temp_output_dir / "test-recipe.jpeg"
    temp_image.write_bytes(TEST_IMAGE.read_bytes())

    expected_output = temp_output_dir / "test-recipe.md"

    # Run CLI without -o flag
    result = subprocess.run(
        [
            "venv/bin/recipe-duck",
            str(temp_image),
            "--api-key",
            api_key,
        ],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert expected_output.exists(), "Default output file was not created"


def test_cli_missing_api_key():
    """Test that CLI fails gracefully when API key is missing."""
    result = subprocess.run(
        [
            "venv/bin/recipe-duck",
            str(TEST_IMAGE),
        ],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        env={},  # Empty environment
    )

    assert result.returncode != 0, "CLI should fail without API key"
    assert "API key required" in result.stderr or "ANTHROPIC_API_KEY" in result.stderr


def test_template_conformance(api_key, temp_output_dir):
    """Test that output conforms to the master template structure."""
    output_file = temp_output_dir / "recipe.md"
    template_file = Path(__file__).parent.parent.parent / "src" / "recipe_duck" / "templates" / "recipe_template.md"

    # Run CLI
    result = subprocess.run(
        [
            "venv/bin/recipe-duck",
            str(TEST_IMAGE),
            "-o",
            str(output_file),
            "--api-key",
            api_key,
        ],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    content = output_file.read_text()
    template = template_file.read_text()

    # Extract section structure from template (markdown headers with their level)
    template_structure = []
    for line in template.split("\n"):
        if line.startswith("#") and not line.startswith("###"):
            # Count the number of # to determine header level
            level = len(line) - len(line.lstrip("#"))
            header_text = line.lstrip("#").strip()
            # Skip placeholder text in brackets
            if not header_text.startswith("[") and header_text:
                template_structure.append((level, header_text))

    # Check that output has the same header structure (but with actual content)
    output_lines = content.split("\n")
    output_headers = []
    for line in output_lines:
        if line.startswith("#") and not line.startswith("###"):
            level = len(line) - len(line.lstrip("#"))
            header_text = line.lstrip("#").strip()
            output_headers.append((level, header_text))

    # Verify we have the right number and level of headers
    assert len(output_headers) >= len(template_structure), \
        f"Expected at least {len(template_structure)} headers, got {len(output_headers)}"

    # Check header levels match the template structure
    for i, (expected_level, template_text) in enumerate(template_structure):
        if i < len(output_headers):
            actual_level, actual_text = output_headers[i]
            assert actual_level == expected_level, \
                f"Header {i+1}: Expected level {expected_level} (e.g., '{'#' * expected_level} {template_text}'), got level {actual_level} ('{('#' * actual_level)} {actual_text}')"

    # Verify structure: title, sections with content
    lines = content.split("\n")

    # First non-empty line should be h1 title
    first_line = next((line for line in lines if line.strip()), "")
    assert first_line.startswith("# "), "First line should be recipe title (# Title)"
    assert len(first_line) > 2, "Title should have actual content, not just '#'"

    # Should have ingredients list items
    assert any(line.strip().startswith("-") for line in lines), "Missing ingredient list items"

    # Should have numbered instructions
    assert any(line.strip().startswith(("1.", "1 ")) for line in lines), "Missing numbered instructions"
