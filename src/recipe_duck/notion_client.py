"""Notion database integration for recipe storage."""

import os
import re
from typing import Optional

from notion_client import Client


class NotionRecipeClient:
    """Client for pushing recipe data to Notion databases."""

    # Database property options
    MEAL_OPTIONS = ["Side", "Breakfast", "Lunch", "Dinner"]
    PROTEIN_OPTIONS = ["Fish", "Veg", "Beef", "Pork", "Turkey", "Chicken"]
    STYLE_OPTIONS = ["Southern", "Mediterranean", "Mexican", "French", "American", "Italian", "Asian"]
    TYPE_OPTIONS = ["Salad", "Low Carb", "Sauce", "Unhealthy", "Healthy", "Fry", "Roast", "Pasta",
                    "Work", "Stove Top", "Grill", "BBQ", "Soup", "Bread", "Dough", "Pizza"]

    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        """
        Initialize Notion client.

        Args:
            api_key: Notion API key. If None, reads from NOTION_API_KEY env var.
            database_id: Notion database ID. If None, reads from NOTION_DATABASE_ID env var.
        """
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID")

        if not self.api_key:
            raise ValueError("Notion API key is required. Set NOTION_API_KEY env var or pass api_key parameter.")

        if not self.database_id:
            raise ValueError("Notion database ID is required. Set NOTION_DATABASE_ID env var or pass database_id parameter.")

        self.client = Client(auth=self.api_key)

    def parse_recipe_markdown(self, markdown: str) -> dict:
        """
        Parse recipe markdown into structured data.

        Args:
            markdown: Recipe markdown string

        Returns:
            Dictionary with recipe components
        """
        # Extract recipe name (first line starting with #)
        name_match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
        name = name_match.group(1) if name_match else "Untitled Recipe"

        # Extract metadata
        prep_time_match = re.search(r'\*\*Prep Time:\*\*\s*([^\n*]+)', markdown)
        cook_time_match = re.search(r'\*\*Cook Time:\*\*\s*([^\n*]+)', markdown)
        total_time_match = re.search(r'\*\*Total Time:\*\*\s*([^\n*]+)', markdown)
        servings_match = re.search(r'\*\*Servings:\*\*\s*([^\n*]+)', markdown)

        # Extract ingredients section
        ingredients_match = re.search(r'##\s+Ingredients\s*\n(.*?)(?=##|$)', markdown, re.DOTALL)
        ingredients = ingredients_match.group(1).strip() if ingredients_match else ""

        # Extract instructions section
        instructions_match = re.search(r'##\s+Instructions\s*\n(.*?)(?=##|$)', markdown, re.DOTALL)
        instructions = instructions_match.group(1).strip() if instructions_match else ""

        # Extract notes section
        notes_match = re.search(r'##\s+Notes\s*\n(.*?)(?=##|$)', markdown, re.DOTALL)
        notes = notes_match.group(1).strip() if notes_match else ""

        return {
            "name": name,
            "prep_time": prep_time_match.group(1).strip() if prep_time_match else "",
            "cook_time": cook_time_match.group(1).strip() if cook_time_match else "",
            "total_time": total_time_match.group(1).strip() if total_time_match else "",
            "servings": servings_match.group(1).strip() if servings_match else "",
            "ingredients": ingredients,
            "instructions": instructions,
            "notes": notes,
        }

    def push_recipe(self, markdown: str) -> str:
        """
        Push recipe to Notion database.

        Args:
            markdown: Recipe markdown string

        Returns:
            URL of the created Notion page
        """
        recipe_data = self.parse_recipe_markdown(markdown)

        # Build properties - only Name is required, rest are optional multi-select
        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": recipe_data["name"]
                        }
                    }
                ]
            }
        }

        # Create page in Notion database
        new_page = self.client.pages.create(
            parent={"database_id": self.database_id},
            properties=properties,
            children=self._build_page_content(recipe_data)
        )

        return new_page["url"]

    def _build_page_content(self, recipe_data: dict) -> list:
        """
        Build Notion page content blocks from recipe data.

        Args:
            recipe_data: Parsed recipe dictionary

        Returns:
            List of Notion block objects
        """
        blocks = []

        # Add ingredients section
        if recipe_data["ingredients"]:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Ingredients"}}]
                }
            })
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": recipe_data["ingredients"]}}]
                }
            })

        # Add instructions section
        if recipe_data["instructions"]:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Instructions"}}]
                }
            })
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": recipe_data["instructions"]}}]
                }
            })

        # Add notes section
        if recipe_data["notes"]:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Notes"}}]
                }
            })
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": recipe_data["notes"]}}]
                }
            })

        return blocks
