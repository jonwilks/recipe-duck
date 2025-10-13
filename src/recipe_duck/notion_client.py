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
        # Match until --- or next ## heading (but not ### subheadings)
        # Use lookahead for ^--- and ^## to not consume them
        ingredients_match = re.search(r'##\s+Ingredients\s*\n(.*?)(?=^---|^##\s[A-Z])', markdown, re.DOTALL | re.MULTILINE)
        if not ingredients_match:
            # Try without lookahead if at end of string
            ingredients_match = re.search(r'##\s+Ingredients\s*\n(.*)', markdown, re.DOTALL | re.MULTILINE)
        ingredients = ingredients_match.group(1).strip() if ingredients_match else ""

        # Extract instructions section
        instructions_match = re.search(r'##\s+Instructions\s*\n(.*?)(?=^---|^##\s[A-Z])', markdown, re.DOTALL | re.MULTILINE)
        if not instructions_match:
            instructions_match = re.search(r'##\s+Instructions\s*\n(.*)', markdown, re.DOTALL | re.MULTILINE)
        instructions = instructions_match.group(1).strip() if instructions_match else ""

        # Extract photos section
        photos_match = re.search(r'##\s+Photos\s*\n(.*?)(?=^---|^##\s[A-Z])', markdown, re.DOTALL | re.MULTILINE)
        if not photos_match:
            photos_match = re.search(r'##\s+Photos\s*\n(.*)', markdown, re.DOTALL | re.MULTILINE)
        photos = photos_match.group(1).strip() if photos_match else ""

        # Extract sources section
        sources_match = re.search(r'##\s+Sources\s*\n(.*?)(?=^---|^##\s[A-Z])', markdown, re.DOTALL | re.MULTILINE)
        if not sources_match:
            sources_match = re.search(r'##\s+Sources\s*\n(.*)', markdown, re.DOTALL | re.MULTILINE)
        sources = sources_match.group(1).strip() if sources_match else ""

        # Extract notes section
        notes_match = re.search(r'##\s+Notes\s*\n(.*?)(?=^---|^##\s[A-Z])', markdown, re.DOTALL | re.MULTILINE)
        if not notes_match:
            notes_match = re.search(r'##\s+Notes\s*\n(.*)', markdown, re.DOTALL | re.MULTILINE)
        notes = notes_match.group(1).strip() if notes_match else ""

        return {
            "name": name,
            "prep_time": prep_time_match.group(1).strip() if prep_time_match else "",
            "cook_time": cook_time_match.group(1).strip() if cook_time_match else "",
            "total_time": total_time_match.group(1).strip() if total_time_match else "",
            "servings": servings_match.group(1).strip() if servings_match else "",
            "ingredients": ingredients,
            "instructions": instructions,
            "photos": photos,
            "sources": sources,
            "notes": notes,
        }

    def push_recipe(self, markdown: str, verbose: bool = False) -> str:
        """
        Push recipe to Notion database.

        Args:
            markdown: Recipe markdown string
            verbose: Enable verbose logging

        Returns:
            URL of the created Notion page
        """
        recipe_data = self.parse_recipe_markdown(markdown)

        if verbose:
            import sys
            print(f"Recipe name: {recipe_data['name']}", file=sys.stderr)
            print(f"Ingredients: {len(recipe_data['ingredients'].split(chr(10)))} lines", file=sys.stderr)
            print(f"Instructions: {len(recipe_data['instructions'].split(chr(10)))} lines", file=sys.stderr)

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
        if verbose:
            import sys
            print(f"🔨 Building Notion page blocks...", file=sys.stderr)

        blocks = self._build_page_content(recipe_data)

        if verbose:
            import sys
            print(f"📦 Created {len(blocks)} Notion blocks", file=sys.stderr)
            print(f"🚀 Creating Notion page...", file=sys.stderr)

        new_page = self.client.pages.create(
            parent={"database_id": self.database_id},
            properties=properties,
            children=blocks
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

        # Add ingredients section with circular bullets
        if recipe_data["ingredients"]:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Ingredients"}}]
                }
            })

            # Parse ingredients into bulleted list items
            ingredient_lines = [line.strip() for line in recipe_data["ingredients"].split("\n") if line.strip()]
            for ingredient_line in ingredient_lines:
                # Remove markdown bullet if present
                ingredient_text = ingredient_line.lstrip("- *")
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": ingredient_text}}]
                    }
                })

            # Add divider
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })

        # Add instructions section with numbered list
        if recipe_data["instructions"]:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Instructions"}}]
                }
            })

            # Parse instructions into numbered list items
            instruction_lines = [line.strip() for line in recipe_data["instructions"].split("\n") if line.strip()]
            for instruction_line in instruction_lines:
                # Skip horizontal rules
                if instruction_line == "---":
                    continue
                # Remove markdown numbering if present
                instruction_text = re.sub(r'^\d+\.\s*', '', instruction_line)
                # Only add if there's actual content after removing numbering
                if instruction_text.strip():
                    blocks.append({
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": instruction_text}}]
                        }
                    })

            # Add divider
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })

        # Add photos section (always show header)
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Photos"}}]
            }
        })
        if recipe_data["photos"]:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": recipe_data["photos"]}}]
                }
            })

        # Add divider
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })

        # Add sources section (always show header)
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Sources"}}]
            }
        })
        if recipe_data["sources"]:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": recipe_data["sources"]}}]
                }
            })

        # Add divider
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })

        # Add notes section (always show header)
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Notes"}}]
            }
        })
        if recipe_data["notes"]:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": recipe_data["notes"]}}]
                }
            })

        return blocks
