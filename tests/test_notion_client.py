"""Tests for Notion client functionality."""

import pytest
from recipe_duck.notion_client import NotionRecipeClient


class TestNotionRecipeClient:
    """Tests for NotionRecipeClient class."""

    def test_parse_basic_recipe(self):
        """Test parsing a basic recipe without subheadings."""
        markdown = """# Chocolate Chip Cookies

**Prep Time:** 15 minutes
**Cook Time:** 12 minutes
**Total Time:** 27 minutes
**Servings:** 24 cookies

---

## Ingredients

- 2 cups - all-purpose flour
- 1 teaspoon - baking soda
- 1 cup - butter

---

## Instructions

1. Preheat oven to 350°F

2. Mix dry ingredients

3. Bake for 12 minutes

---

## Notes

Best served warm!
"""
        client = NotionRecipeClient(api_key="fake_key", database_id="fake_db_id")
        result = client.parse_recipe_markdown(markdown)

        assert result["name"] == "Chocolate Chip Cookies"
        assert result["prep_time"] == "15 minutes"
        assert result["cook_time"] == "12 minutes"
        assert result["total_time"] == "27 minutes"
        assert result["servings"] == "24 cookies"
        assert "2 cups - all-purpose flour" in result["ingredients"]
        assert "Preheat oven to 350°F" in result["instructions"]
        assert "Mix dry ingredients" in result["instructions"]
        assert "Best served warm!" in result["notes"]

    def test_parse_instructions_with_subheadings(self):
        """Test that instructions with ### subheadings are fully captured.

        This is a regression test for recipes with multiple cooking methods
        (e.g., Stove Top vs Instant Pot) that use subheadings.
        """
        markdown = """# Couscous Chicken Soup

**Prep Time:** 10 minutes
**Cook Time:** 20 minutes
**Total Time:** 30 minutes
**Servings:** 6

---

## Ingredients

- 1 tablespoon - olive oil
- 2 cups - chicken broth
- 1 cup - couscous

---

## Instructions

### Stove Top Version:

1. Heat one tablespoon of the stock in a Dutch oven over medium

2. Add the onions, leeks, carrots, and celery

3. Cook for 15 minutes

### Instant Pot Version:

1. Turn on the Saute function on your IP

2. Add the oil and heat until shimmering

3. Set the Instant Pot to manual high pressure for 5 minutes

---

## Notes

Both methods work great!
"""
        client = NotionRecipeClient(api_key="fake_key", database_id="fake_db_id")
        result = client.parse_recipe_markdown(markdown)

        # The bug: current regex stops at ### because it matches the "##" lookahead
        # All instructions content should be captured, including subheadings
        assert "### Stove Top Version:" in result["instructions"], \
            "Should capture Stove Top subheading"
        assert "### Instant Pot Version:" in result["instructions"], \
            "Should capture Instant Pot subheading"
        assert "Heat one tablespoon of the stock" in result["instructions"], \
            "Should capture first stove top instruction"
        assert "Turn on the Saute function" in result["instructions"], \
            "Should capture first instant pot instruction"
        assert "Set the Instant Pot to manual high pressure" in result["instructions"], \
            "Should capture last instant pot instruction"

    def test_parse_ingredients_with_subheadings(self):
        """Test that ingredients with ### subheadings are fully captured."""
        markdown = """# Test Recipe

## Ingredients

### For the Dough:

- 2 cups - flour
- 1 teaspoon - salt

### For the Filling:

- 1 cup - cheese
- 2 tablespoons - herbs

---

## Instructions

1. Make the dough

---
"""
        client = NotionRecipeClient(api_key="fake_key", database_id="fake_db_id")
        result = client.parse_recipe_markdown(markdown)

        # Should capture all ingredients including subheadings
        assert "### For the Dough:" in result["ingredients"]
        assert "### For the Filling:" in result["ingredients"]
        assert "2 cups - flour" in result["ingredients"]
        assert "1 cup - cheese" in result["ingredients"]

    def test_parse_empty_sections(self):
        """Test parsing recipe with empty sections."""
        markdown = """# Simple Recipe

## Ingredients

- 1 cup - water

---

## Instructions

1. Boil water

---

## Photos

---

## Sources

---

## Notes

---
"""
        client = NotionRecipeClient(api_key="fake_key", database_id="fake_db_id")
        result = client.parse_recipe_markdown(markdown)

        assert result["name"] == "Simple Recipe"
        assert "1 cup - water" in result["ingredients"]
        assert "Boil water" in result["instructions"]
        assert result["photos"] == ""
        assert result["sources"] == ""
        assert result["notes"] == ""

    def test_parse_recipe_without_metadata(self):
        """Test parsing recipe without prep time, cook time, etc."""
        markdown = """# Quick Recipe

## Ingredients

- Salt

---

## Instructions

1. Add salt

---
"""
        client = NotionRecipeClient(api_key="fake_key", database_id="fake_db_id")
        result = client.parse_recipe_markdown(markdown)

        assert result["name"] == "Quick Recipe"
        assert result["prep_time"] == ""
        assert result["cook_time"] == ""
        assert result["total_time"] == ""
        assert result["servings"] == ""
