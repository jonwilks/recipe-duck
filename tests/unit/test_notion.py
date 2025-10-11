"""Tests for Notion integration."""

import pytest
from recipe_duck.notion_client import NotionRecipeClient


def test_parse_recipe_markdown():
    """Test parsing recipe markdown into structured data."""
    markdown = """# Chocolate Chip Cookies

**Prep Time:** 15 minutes
**Cook Time:** 12 minutes
**Total Time:** 27 minutes
**Servings:** 24 cookies

## Ingredients

- 2 1/4 cups all-purpose flour
- 1 tsp baking soda
- 1 cup butter, softened
- 3/4 cup sugar

## Instructions

1. Preheat oven to 375°F
2. Mix flour and baking soda
3. Beat butter and sugars

## Notes

Store in airtight container for up to 1 week.
"""

    # Note: This test doesn't require actual API credentials
    # We're just testing the parsing logic
    client = NotionRecipeClient.__new__(NotionRecipeClient)
    result = client.parse_recipe_markdown(markdown)

    assert result["name"] == "Chocolate Chip Cookies"
    assert result["prep_time"] == "15 minutes"
    assert result["cook_time"] == "12 minutes"
    assert result["total_time"] == "27 minutes"
    assert result["servings"] == "24 cookies"
    assert "2 1/4 cups all-purpose flour" in result["ingredients"]
    assert "Preheat oven to 375°F" in result["instructions"]
    assert "Store in airtight container" in result["notes"]


def test_parse_recipe_markdown_minimal():
    """Test parsing minimal recipe markdown."""
    markdown = """# Simple Recipe

## Ingredients

- Item 1

## Instructions

1. Step 1
"""

    client = NotionRecipeClient.__new__(NotionRecipeClient)
    result = client.parse_recipe_markdown(markdown)

    assert result["name"] == "Simple Recipe"
    assert result["prep_time"] == ""
    assert result["cook_time"] == ""
    assert result["total_time"] == ""
    assert result["servings"] == ""
    assert "Item 1" in result["ingredients"]
    assert "Step 1" in result["instructions"]
    assert result["notes"] == ""


def test_notion_client_requires_api_key(monkeypatch):
    """Test that NotionRecipeClient requires API key."""
    # Clear environment variables
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

    with pytest.raises(ValueError, match="Notion API key is required"):
        NotionRecipeClient(api_key=None, database_id="test_db_id")


def test_notion_client_requires_database_id(monkeypatch):
    """Test that NotionRecipeClient requires database ID."""
    # Clear environment variables
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

    with pytest.raises(ValueError, match="Notion database ID is required"):
        NotionRecipeClient(api_key="test_api_key", database_id=None)


def test_build_page_content():
    """Test building Notion page content blocks."""
    client = NotionRecipeClient.__new__(NotionRecipeClient)

    recipe_data = {
        "name": "Test Recipe",
        "prep_time": "10 min",
        "cook_time": "20 min",
        "total_time": "30 min",
        "servings": "4",
        "ingredients": "- Ingredient 1\n- Ingredient 2",
        "instructions": "1. Step 1\n2. Step 2",
        "photos": "",
        "sources": "",
        "notes": "Some notes here",
    }

    blocks = client._build_page_content(recipe_data)

    # Should have:
    # - Ingredients heading + 2 bullet items + divider = 4
    # - Instructions heading + 2 numbered items + divider = 4
    # - Photos heading + divider = 2
    # - Sources heading + divider = 2
    # - Notes heading + paragraph = 2
    # Total = 14
    assert len(blocks) == 14

    # Check that we have the right section headings
    heading_blocks = [b for b in blocks if b["type"] == "heading_2"]
    assert len(heading_blocks) == 5

    heading_texts = [b["heading_2"]["rich_text"][0]["text"]["content"] for b in heading_blocks]
    assert "Ingredients" in heading_texts
    assert "Instructions" in heading_texts
    assert "Photos" in heading_texts
    assert "Sources" in heading_texts
    assert "Notes" in heading_texts

    # Check ingredients are bulleted list items
    ingredient_blocks = [b for b in blocks if b["type"] == "bulleted_list_item"]
    assert len(ingredient_blocks) == 2

    # Check instructions are numbered list items
    instruction_blocks = [b for b in blocks if b["type"] == "numbered_list_item"]
    assert len(instruction_blocks) == 2
