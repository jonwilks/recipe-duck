"""Notion database integration for recipe storage."""

import os
import re
from typing import Optional

from notion_client import Client


class NotionRecipeClient:
    """Client for pushing recipe data to Notion databases."""

    # Database property options (for reference - may be overridden by actual database schema)
    CUISINE_OPTIONS = ["Moroccan", "Caribbean", "Vietnamese", "Turkish", "Lebanese", "Brazilian",
                       "Korean", "Spanish", "Thai", "Indian", "Southern", "Greek", "Mexican",
                       "French", "American", "Italian", "Chinese"]

    PROTEIN_OPTIONS = ["Fish", "Veg", "Beef", "Pork", "Turkey", "Chicken"]

    COURSE_OPTIONS = ["Dinner", "Lunch", "Breakfast", "Sauce", "Salad", "Main Course",
                      "Soup", "Dessert", "Side", "Appetizer", "Beverage"]

    METHOD_OPTIONS = ["Smoking", "Baking", "Blanching", "Microwaving", "Sautéing",
                      "Broiling", "No-Cook", "Marinating", "Pickling", "Braising",
                      "Steaming", "Oven", "Fry", "Roast", "Stove Top", "Grill",
                      "BBQ", "Crockpot"]

    EFFORT_OPTIONS = ["🔪", "🔪🔪", "🔪🔪🔪"]

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

        # Extract properties line (cuisine, protein, course, method, effort, rating, cook time)
        # Updated pattern to match new property names
        properties_match = re.search(r'\*Cuisine:\s*([^|]+)\s*\|\s*Protein:\s*([^|]+)\s*\|\s*Course:\s*([^|]+)\s*\|\s*Method:\s*([^|]+)\s*\|\s*Effort:\s*([^|]+)\s*\|\s*Rating:\s*([^|]+)\s*\|\s*Cook Time:\s*([^*]+)\*', markdown)
        cuisine = properties_match.group(1).strip() if properties_match else ""
        protein = properties_match.group(2).strip() if properties_match else ""
        course = properties_match.group(3).strip() if properties_match else ""
        method = properties_match.group(4).strip() if properties_match else ""
        effort = properties_match.group(5).strip() if properties_match else ""
        rating = properties_match.group(6).strip() if properties_match else ""
        cook_time_prop = properties_match.group(7).strip() if properties_match else ""

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

        # Extract directions section
        directions_match = re.search(r'##\s+Directions\s*\n(.*?)(?=^---|^##\s[A-Z])', markdown, re.DOTALL | re.MULTILINE)
        if not directions_match:
            directions_match = re.search(r'##\s+Directions\s*\n(.*)', markdown, re.DOTALL | re.MULTILINE)
        directions = directions_match.group(1).strip() if directions_match else ""

        # Extract photos section
        photos_match = re.search(r'##\s+Photos\s*\n(.*?)(?=^---|^##\s[A-Z])', markdown, re.DOTALL | re.MULTILINE)
        if not photos_match:
            photos_match = re.search(r'##\s+Photos\s*\n(.*)', markdown, re.DOTALL | re.MULTILINE)
        photos = photos_match.group(1).strip() if photos_match else ""

        # Extract links section
        links_match = re.search(r'##\s+Links\s*\n(.*?)(?=^---|^##\s[A-Z])', markdown, re.DOTALL | re.MULTILINE)
        if not links_match:
            links_match = re.search(r'##\s+Links\s*\n(.*)', markdown, re.DOTALL | re.MULTILINE)
        links = links_match.group(1).strip() if links_match else ""

        # Extract notes section
        notes_match = re.search(r'##\s+Notes\s*\n(.*?)(?=^---|^##\s[A-Z])', markdown, re.DOTALL | re.MULTILINE)
        if not notes_match:
            notes_match = re.search(r'##\s+Notes\s*\n(.*)', markdown, re.DOTALL | re.MULTILINE)
        notes = notes_match.group(1).strip() if notes_match else ""

        # Extract nutrition section
        nutrition_match = re.search(r'##\s+Nutrition\s*\n(.*?)(?=^---|^##\s[A-Z])', markdown, re.DOTALL | re.MULTILINE)
        if not nutrition_match:
            nutrition_match = re.search(r'##\s+Nutrition\s*\n(.*)', markdown, re.DOTALL | re.MULTILINE)
        nutrition = nutrition_match.group(1).strip() if nutrition_match else ""

        return {
            "name": name,
            "cuisine": cuisine,
            "protein": protein,
            "course": course,
            "method": method,
            "effort": effort,
            "rating": rating,
            "cook_time_prop": cook_time_prop,
            "prep_time": prep_time_match.group(1).strip() if prep_time_match else "",
            "cook_time": cook_time_match.group(1).strip() if cook_time_match else "",
            "total_time": total_time_match.group(1).strip() if total_time_match else "",
            "servings": servings_match.group(1).strip() if servings_match else "",
            "ingredients": ingredients,
            "directions": directions,
            "notes": notes,
            "links": links,
            "nutrition": nutrition,
            "photos": photos,
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
            print(f"Cuisine: {recipe_data.get('cuisine', 'N/A')}", file=sys.stderr)
            print(f"Protein: {recipe_data.get('protein', 'N/A')}", file=sys.stderr)
            print(f"Course: {recipe_data.get('course', 'N/A')}", file=sys.stderr)
            print(f"Method: {recipe_data.get('method', 'N/A')}", file=sys.stderr)
            print(f"Effort: {recipe_data.get('effort', 'N/A')}", file=sys.stderr)
            print(f"Rating: {recipe_data.get('rating', 'N/A')}", file=sys.stderr)
            print(f"Cook Time: {recipe_data.get('cook_time_prop') or recipe_data.get('cook_time', 'N/A')}", file=sys.stderr)
            print(f"Ingredients: {len(recipe_data['ingredients'].split(chr(10)))} lines", file=sys.stderr)
            print(f"Directions: {len(recipe_data['directions'].split(chr(10)))} lines", file=sys.stderr)

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

        # Add Cuisine property if present
        if recipe_data.get("cuisine"):
            # Split by comma if multiple values
            cuisine_values = [c.strip() for c in recipe_data["cuisine"].split(",")]
            properties["Cuisine"] = {
                "multi_select": [{"name": val} for val in cuisine_values if val]
            }

        # Add Protein property if present
        if recipe_data.get("protein"):
            protein_values = [p.strip() for p in recipe_data["protein"].split(",")]
            properties["Protein"] = {
                "multi_select": [{"name": val} for val in protein_values if val]
            }

        # Add Course property if present
        if recipe_data.get("course"):
            course_values = [c.strip() for c in recipe_data["course"].split(",")]
            properties["Course"] = {
                "multi_select": [{"name": val} for val in course_values if val]
            }

        # Add Method property if present (renamed from Cooking Method)
        if recipe_data.get("method"):
            method_values = [m.strip() for m in recipe_data["method"].split(",")]
            properties["Method"] = {
                "multi_select": [{"name": val} for val in method_values if val]
            }

        # Add Effort property if present (select type with knife emojis)
        if recipe_data.get("effort"):
            properties["Effort"] = {
                "select": {"name": recipe_data["effort"].strip()}
            }

        # Add Rating property if present (select type)
        if recipe_data.get("rating"):
            properties["Rating"] = {
                "select": {"name": recipe_data["rating"].strip()}
            }

        # Create page in Notion database
        if verbose:
            import sys
            print(f"Building Notion page blocks...", file=sys.stderr)

        blocks = self._build_page_content(recipe_data)

        if verbose:
            import sys
            print(f"Created {len(blocks)} Notion blocks", file=sys.stderr)
            print(f"Creating Notion page...", file=sys.stderr)

        # Try to create the page with all properties
        try:
            new_page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=blocks
            )
            return new_page["url"]
        except Exception as e:
            # If a property doesn't exist, retry with only Name property
            import sys
            error_msg = str(e)
            if "is not a property that exists" in error_msg:
                # Extract which property failed
                failed_prop = error_msg.split("is not a property")[0].strip()
                if verbose:
                    print(f"⚠️  Property '{failed_prop}' not found in database, retrying without optional properties...", file=sys.stderr)

                # Retry with only Name property
                minimal_properties = {
                    "Name": properties["Name"]
                }

                new_page = self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties=minimal_properties,
                    children=blocks
                )

                if verbose:
                    print(f"⚠️  Page created without properties: {', '.join([k for k in properties.keys() if k != 'Name'])}", file=sys.stderr)
                    print(f"💡 To use properties, add these fields to your Notion database:", file=sys.stderr)
                    print(f"   - Cuisine (multi-select)", file=sys.stderr)
                    print(f"   - Protein (multi-select)", file=sys.stderr)
                    print(f"   - Course (multi-select)", file=sys.stderr)
                    print(f"   - Method (multi-select)", file=sys.stderr)
                    print(f"   - Effort (select)", file=sys.stderr)
                    print(f"   - Rating (select)", file=sys.stderr)

                return new_page["url"]
            else:
                # Re-raise if it's a different error
                raise

    def _build_page_content(self, recipe_data: dict) -> list:
        """
        Build Notion page content blocks from recipe data.

        Order matches recipe_template.md:
        1. Ingredients
        2. Directions
        3. Notes
        4. Links
        5. Nutrition
        6. Photos

        Args:
            recipe_data: Parsed recipe dictionary

        Returns:
            List of Notion block objects
        """
        blocks = []

        # 1. Add ingredients section with tables
        if recipe_data["ingredients"]:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Ingredients"}}]
                }
            })

            # Parse ingredients - can have multiple tables separated by subheadings
            ingredient_content = recipe_data["ingredients"]
            ingredient_lines = ingredient_content.split("\n")

            i = 0
            while i < len(ingredient_lines):
                line = ingredient_lines[i].strip()

                # Check for subheading (### heading)
                if line.startswith("###"):
                    subheading_text = line.lstrip("#").strip()
                    blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": subheading_text}}]
                        }
                    })
                    i += 1
                    continue

                # Check for table header (starts with |)
                if line.startswith("|") and "Ingredient" in line:
                    # Found a table - collect all table rows
                    table_rows = []
                    i += 1  # Skip header row

                    # Skip separator row (|---|---|---|)
                    if i < len(ingredient_lines) and "---" in ingredient_lines[i]:
                        i += 1

                    # Collect data rows
                    while i < len(ingredient_lines):
                        row_line = ingredient_lines[i].strip()
                        if not row_line or not row_line.startswith("|"):
                            break

                        # Parse the table row: | ingredient | measurement | method |
                        parts = [p.strip() for p in row_line.split("|")[1:-1]]  # Remove first and last empty elements
                        if len(parts) >= 3:
                            table_rows.append({
                                "ingredient": parts[0],
                                "measurement": parts[1],
                                "method": parts[2]
                            })
                        i += 1

                    # Create Notion table block
                    if table_rows:
                        # Notion tables need width, height, and cells
                        table_width = 3  # 3 columns
                        table_height = len(table_rows) + 1  # +1 for header row

                        # Build table block with code formatting (monospace font)
                        blocks.append({
                            "object": "block",
                            "type": "table",
                            "table": {
                                "table_width": table_width,
                                "has_column_header": True,
                                "has_row_header": False,
                                "children": [
                                    # Header row
                                    {
                                        "type": "table_row",
                                        "table_row": {
                                            "cells": [
                                                [{"type": "text", "text": {"content": "Ingredient"}}],
                                                [{"type": "text", "text": {"content": "Measurement"}}],
                                                [{"type": "text", "text": {"content": "Method"}}]
                                            ]
                                        }
                                    }
                                ] + [
                                    # Data rows with code annotations for monospace font
                                    {
                                        "type": "table_row",
                                        "table_row": {
                                            "cells": [
                                                [{"type": "text", "text": {"content": row["ingredient"]}, "annotations": {"code": True}}],
                                                [{"type": "text", "text": {"content": row["measurement"]}, "annotations": {"code": True}}],
                                                [{"type": "text", "text": {"content": row["method"]}, "annotations": {"code": True}}]
                                            ]
                                        }
                                    } for row in table_rows
                                ]
                            }
                        })
                    continue

                i += 1

            # Add divider
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })

        # 2. Add directions section with numbered list
        if recipe_data["directions"]:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Directions"}}]
                }
            })

            # Parse directions into numbered list items, handling subheadings
            direction_lines = [line.strip() for line in recipe_data["directions"].split("\n") if line.strip()]
            for direction_line in direction_lines:
                # Skip horizontal rules
                if direction_line == "---":
                    continue

                # Check if this is a subheading (### heading)
                if direction_line.startswith("###"):
                    subheading_text = direction_line.lstrip("#").strip()
                    blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": subheading_text}}]
                        }
                    })
                    continue

                # Remove markdown numbering if present
                direction_text = re.sub(r'^\d+\.\s*', '', direction_line)
                # Only add if there's actual content after removing numbering
                if direction_text.strip():
                    blocks.append({
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": direction_text}}]
                        }
                    })

            # Add divider
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })

        # 3. Add notes section (always show header)
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

        # Add divider
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })

        # 4. Add links section (always show header)
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Links"}}]
            }
        })
        if recipe_data["links"]:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": recipe_data["links"]}}]
                }
            })

        # Add divider
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })

        # 5. Add nutrition section (always show header)
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Nutrition"}}]
            }
        })
        if recipe_data.get("nutrition"):
            # Nutrition can be multi-line, add as paragraph
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": recipe_data["nutrition"]}}]
                }
            })

        # Add divider
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })

        # 6. Add photos section (always show header)
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

        return blocks
