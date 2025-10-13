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

    COOKING_METHOD_OPTIONS = ["Smoking", "Baking", "Blanching", "Microwaving", "Sautéing",
                              "Broiling", "No-Cook", "Marinating", "Pickling", "Braising",
                              "Steaming", "Oven", "Fry", "Roast", "Stove Top", "Grill",
                              "BBQ", "Crockpot"]

    # Legacy options (kept for backwards compatibility)
    MEAL_OPTIONS = ["Side", "Breakfast", "Lunch", "Dinner"]
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

        # Extract properties line (cuisine, protein, course, cooking method, cook time)
        properties_match = re.search(r'\*Cuisine:\s*([^|]+)\s*\|\s*Protein:\s*([^|]+)\s*\|\s*Course:\s*([^|]+)\s*\|\s*Cooking Method:\s*([^|]+)\s*\|\s*Cook Time:\s*([^*]+)\*', markdown)
        cuisine = properties_match.group(1).strip() if properties_match else ""
        protein = properties_match.group(2).strip() if properties_match else ""
        course = properties_match.group(3).strip() if properties_match else ""
        cooking_method = properties_match.group(4).strip() if properties_match else ""
        cook_time_prop = properties_match.group(5).strip() if properties_match else ""

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
            "cooking_method": cooking_method,
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
            print(f"Cooking Method: {recipe_data.get('cooking_method', 'N/A')}", file=sys.stderr)
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

        # Add Cooking Method property if present
        if recipe_data.get("cooking_method"):
            method_values = [m.strip() for m in recipe_data["cooking_method"].split(",")]
            properties["Cooking Method"] = {
                "multi_select": [{"name": val} for val in method_values if val]
            }

        # Add Cooking Time property if present (use cook_time_prop from properties line, or fallback to metadata)
        cook_time_value = recipe_data.get("cook_time_prop") or recipe_data.get("cook_time")
        if cook_time_value:
            properties["Cooking Time"] = {
                "rich_text": [{"type": "text", "text": {"content": cook_time_value}}]
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
                    print(f"   - Cooking Method (multi-select)", file=sys.stderr)
                    print(f"   - Cooking Time (text)", file=sys.stderr)

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

        # 1. Add ingredients section with circular bullets
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

        # 2. Add directions section with numbered list
        if recipe_data["directions"]:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Directions"}}]
                }
            })

            # Parse directions into numbered list items
            direction_lines = [line.strip() for line in recipe_data["directions"].split("\n") if line.strip()]
            for direction_line in direction_lines:
                # Skip horizontal rules
                if direction_line == "---":
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
