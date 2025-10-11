"""Integration tests for URL recipe processing."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from recipe_duck.processor import RecipeProcessor


# Test URLs (using mock data in tests)
TEST_URL = "https://www.example.com/recipe/chocolate-chip-cookies"


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


@pytest.fixture
def sample_recipe_html():
    """Sample HTML with recipe data."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chocolate Chip Cookies Recipe</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Chocolate Chip Cookies",
            "prepTime": "PT15M",
            "cookTime": "PT12M",
            "totalTime": "PT27M",
            "recipeYield": "24 cookies",
            "recipeIngredient": [
                "2 1/4 cups all-purpose flour",
                "1 teaspoon baking soda",
                "1 cup butter, softened",
                "3/4 cup granulated sugar",
                "3/4 cup packed brown sugar",
                "2 large eggs",
                "2 teaspoons vanilla extract",
                "2 cups chocolate chips"
            ],
            "recipeInstructions": [
                {
                    "@type": "HowToStep",
                    "text": "Preheat oven to 375 degrees F"
                },
                {
                    "@type": "HowToStep",
                    "text": "Combine flour and baking soda in a bowl"
                },
                {
                    "@type": "HowToStep",
                    "text": "Beat butter and sugars until creamy"
                },
                {
                    "@type": "HowToStep",
                    "text": "Add eggs and vanilla, mix well"
                },
                {
                    "@type": "HowToStep",
                    "text": "Gradually blend in flour mixture"
                },
                {
                    "@type": "HowToStep",
                    "text": "Stir in chocolate chips"
                },
                {
                    "@type": "HowToStep",
                    "text": "Drop by rounded tablespoon onto ungreased cookie sheets"
                },
                {
                    "@type": "HowToStep",
                    "text": "Bake 9 to 11 minutes or until golden brown"
                }
            ]
        }
        </script>
    </head>
    <body>
        <h1>Chocolate Chip Cookies</h1>
        <p>The best chocolate chip cookies recipe!</p>
    </body>
    </html>
    """


def test_url_detection():
    """Test URL detection function."""
    from recipe_duck.cli import is_url

    assert is_url("https://example.com/recipe")
    assert is_url("http://example.com/recipe")
    assert not is_url("/path/to/image.jpg")
    assert not is_url("image.jpg")
    assert not is_url("C:\\path\\to\\image.jpg")


def test_filename_generation_from_url():
    """Test filename generation from URLs."""
    from recipe_duck.cli import generate_filename_from_url

    assert generate_filename_from_url("https://example.com/recipe/chocolate-chip-cookies") == "chocolate_chip_cookies"
    assert generate_filename_from_url("https://example.com/recipes/12345/best-pasta") == "best_pasta"
    assert generate_filename_from_url("https://example.com/") == "recipe"
    assert generate_filename_from_url("https://example.com/recipe/test-recipe-name") == "test_recipe_name"


@patch("recipe_duck.url_extractor.requests.get")
def test_process_url_with_structured_data(mock_get, api_key, sample_recipe_html):
    """Test processing URL with structured data (mocked network call)."""
    # Mock the HTTP request
    mock_response = Mock()
    mock_response.text = sample_recipe_html
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    processor = RecipeProcessor(api_key=api_key, model="claude-3-5-haiku-20241022")

    # Process the mocked URL
    markdown = processor.process_url(TEST_URL, verbose=False)

    # Verify the request was made
    mock_get.assert_called_once()

    # Verify output format
    assert markdown is not None
    assert len(markdown) > 0
    assert "# " in markdown  # Should have a title
    assert "## Ingredients" in markdown or "Ingredients" in markdown
    assert "## Instructions" in markdown or "Instructions" in markdown


@patch("recipe_duck.url_extractor.requests.get")
def test_cli_with_url(mock_get, api_key, temp_output_dir, sample_recipe_html):
    """Test CLI with URL input (mocked network call)."""
    # Mock the HTTP request
    mock_response = Mock()
    mock_response.text = sample_recipe_html
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    output_file = temp_output_dir / "test-recipe.md"

    # Run CLI command with URL
    result = subprocess.run(
        [
            "venv/bin/recipe-duck",
            TEST_URL,
            "-o",
            str(output_file),
            "--api-key",
            api_key,
            "--cheap",  # Use cheaper model for tests
        ],
        cwd=Path(__file__).parent.parent.parent,
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Check command succeeded
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Check output file was created
    assert output_file.exists(), "Output markdown file was not created"

    # Read and verify content
    content = output_file.read_text()
    assert len(content) > 0
    assert "# " in content  # Should have a title


@patch("recipe_duck.url_extractor.requests.get")
def test_cli_url_default_output_filename(mock_get, api_key, temp_output_dir, sample_recipe_html):
    """Test that CLI generates appropriate filename for URL input."""
    # Mock the HTTP request
    mock_response = Mock()
    mock_response.text = sample_recipe_html
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Change to temp directory
    original_dir = os.getcwd()
    try:
        os.chdir(temp_output_dir)

        # Run CLI without -o flag
        result = subprocess.run(
            [
                "venv/bin/recipe-duck",
                "https://example.com/recipe/chocolate-chip-cookies",
                "--api-key",
                api_key,
                "--cheap",
            ],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Check that a .md file was created with expected name
        md_files = list(temp_output_dir.glob("*.md"))
        assert len(md_files) == 1, f"Expected 1 .md file, found {len(md_files)}"

        # Filename should be derived from URL
        assert "chocolate" in md_files[0].name.lower() or "cookies" in md_files[0].name.lower() or "recipe" in md_files[0].name.lower()

    finally:
        os.chdir(original_dir)


@patch("recipe_duck.url_extractor.requests.get")
def test_url_with_verbose_flag(mock_get, api_key, temp_output_dir, sample_recipe_html):
    """Test verbose output for URL processing."""
    # Mock the HTTP request
    mock_response = Mock()
    mock_response.text = sample_recipe_html
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    output_file = temp_output_dir / "verbose-test.md"

    result = subprocess.run(
        [
            "venv/bin/recipe-duck",
            TEST_URL,
            "-o",
            str(output_file),
            "--api-key",
            api_key,
            "--cheap",
            "-v",
        ],
        cwd=Path(__file__).parent.parent.parent,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0

    # Check verbose output includes URL processing info
    # Note: verbose output goes to stderr
    stderr = result.stderr.lower()
    # Should mention URL or fetching
    assert "url" in stderr or "fetch" in stderr or "processing" in stderr


@patch("recipe_duck.url_extractor.requests.get")
def test_url_with_formatting_disabled(mock_get, api_key, temp_output_dir, sample_recipe_html):
    """Test URL processing with formatting disabled."""
    # Mock the HTTP request
    mock_response = Mock()
    mock_response.text = sample_recipe_html
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    output_file = temp_output_dir / "no-format.md"

    result = subprocess.run(
        [
            "venv/bin/recipe-duck",
            TEST_URL,
            "-o",
            str(output_file),
            "--api-key",
            api_key,
            "--cheap",
            "--no-format",
        ],
        cwd=Path(__file__).parent.parent.parent,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    assert output_file.exists()


def test_url_error_handling_invalid_url(api_key):
    """Test error handling for invalid URLs."""
    processor = RecipeProcessor(api_key=api_key)

    with pytest.raises(Exception):
        processor.process_url("https://this-is-a-fake-url-that-does-not-exist-12345.com/recipe")


@patch("recipe_duck.url_extractor.requests.get")
def test_url_error_handling_timeout(mock_get, api_key):
    """Test handling of timeout errors."""
    import requests

    mock_get.side_effect = requests.Timeout()

    processor = RecipeProcessor(api_key=api_key)

    with pytest.raises(Exception, match="took too long"):
        processor.process_url(TEST_URL)


@patch("recipe_duck.url_extractor.requests.get")
def test_process_url_without_structured_data(mock_get, api_key):
    """Test processing URL without JSON-LD (fallback to HTML parsing)."""
    # HTML without JSON-LD
    html_without_jsonld = """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="recipe">
            <h1>Simple Pasta Recipe</h1>
            <div class="ingredients">
                <h2>Ingredients</h2>
                <ul>
                    <li>1 lb pasta</li>
                    <li>2 cups tomato sauce</li>
                </ul>
            </div>
            <div class="instructions">
                <h2>Instructions</h2>
                <ol>
                    <li>Boil water and cook pasta</li>
                    <li>Heat sauce and combine</li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    """

    mock_response = Mock()
    mock_response.text = html_without_jsonld
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    processor = RecipeProcessor(api_key=api_key, model="claude-3-5-haiku-20241022")
    markdown = processor.process_url(TEST_URL, verbose=False)

    assert markdown is not None
    assert len(markdown) > 0
