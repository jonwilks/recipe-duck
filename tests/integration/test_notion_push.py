#!/usr/bin/env python3
"""Test script to push a sample recipe to Notion database."""

import os
from dotenv import load_dotenv
from recipe_duck.notion_client import NotionRecipeClient

# Load environment variables
load_dotenv()

# Sample recipe markdown
SAMPLE_RECIPE = """# Chocolate Chip Cookies

**Prep Time:** 15 minutes
**Cook Time:** 12 minutes
**Total Time:** 27 minutes
**Servings:** 24 cookies

## Ingredients

- 2 1/4 cups all-purpose flour
- 1 tsp baking soda
- 1 tsp salt
- 1 cup (2 sticks) butter, softened
- 3/4 cup granulated sugar
- 3/4 cup packed brown sugar
- 2 large eggs
- 2 tsp vanilla extract
- 2 cups chocolate chips

## Instructions

1. Preheat oven to 375°F (190°C)
2. Mix flour, baking soda, and salt in a bowl
3. In a separate bowl, beat butter, granulated sugar, and brown sugar until creamy
4. Add eggs and vanilla to butter mixture and beat well
5. Gradually blend in flour mixture
6. Stir in chocolate chips
7. Drop rounded tablespoons onto ungreased cookie sheets
8. Bake for 9-11 minutes or until golden brown
9. Cool on baking sheets for 2 minutes, then transfer to wire racks

## Notes

Store in airtight container for up to 1 week. For chewier cookies, slightly underbake them. You can freeze the dough for up to 3 months.
"""


def main():
    """Push sample recipe to Notion."""
    print("🦆 Recipe Duck - Notion Integration Test\n")

    # Get credentials from environment
    notion_api_key = os.getenv("NOTION_API_KEY")
    notion_database_id = os.getenv("NOTION_DATABASE_ID")

    if not notion_api_key:
        print("❌ Error: NOTION_API_KEY not found in .env file")
        return

    if not notion_database_id:
        print("❌ Error: NOTION_DATABASE_ID not found in .env file")
        return

    print(f"📝 Pushing sample recipe to Notion database...")
    print(f"   Database ID: {notion_database_id[:8]}...\n")

    try:
        # Initialize Notion client
        client = NotionRecipeClient(
            api_key=notion_api_key,
            database_id=notion_database_id
        )

        # Push the sample recipe
        page_url = client.push_recipe(SAMPLE_RECIPE)

        print("✅ Success!")
        print(f"   Recipe page URL: {page_url}")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
