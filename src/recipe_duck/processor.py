"""Core recipe processing logic."""

import base64
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from PIL import Image


class RecipeProcessor:
    """Processes recipe images and converts them to markdown."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        template_path: Path | None = None,
    ):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.template = self._load_template(template_path)

    def _load_template(self, template_path: Path | None) -> str:
        """Load the master recipe template.

        Args:
            template_path: Optional custom template path. If None, uses default.

        Returns:
            Template content as string
        """
        if template_path is None:
            # Default to recipe_template.md in templates directory
            template_path = Path(__file__).parent / "templates" / "recipe_template.md"

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        return template_path.read_text()

    def process_image(self, image_path: Path) -> str:
        """Process a recipe image and return markdown content.

        Args:
            image_path: Path to the recipe image file

        Returns:
            Markdown formatted recipe content
        """
        # Load and encode image
        image_data = self._encode_image(image_path)

        # Get structured recipe data from Claude
        markdown = self._extract_recipe(image_data)

        return markdown

    def _encode_image(self, image_path: Path) -> dict[str, Any]:
        """Encode image for API submission.

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with image data for API
        """
        # Open and potentially resize image to reduce API costs
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            # Read file bytes
            with open(image_path, "rb") as f:
                image_bytes = f.read()

        # Determine media type
        suffix = image_path.suffix.lower()
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_type_map.get(suffix, "image/jpeg")

        # Encode to base64
        encoded = base64.standard_b64encode(image_bytes).decode("utf-8")

        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": encoded,
            },
        }

    def _extract_recipe(self, image_data: dict[str, Any]) -> str:
        """Extract recipe information using Claude Vision API.

        Args:
            image_data: Encoded image data

        Returns:
            Markdown formatted recipe
        """
        prompt = f"""Analyze this recipe image and extract the recipe information into a structured markdown format.

You MUST follow this exact template structure:

{self.template}

Instructions:
- Extract all text accurately from the image, preserving measurements and quantities
- Fill in the template with the actual recipe information
- Use the exact section headers shown in the template (# Title, ## Ingredients, ## Instructions, ## Notes)
- For Ingredients: Use bullet points (-) with quantities and units when visible
- For Instructions: Use numbered lists (1., 2., 3., etc.) with clear, actionable steps
- If any section is not visible in the image, include the header but note that information is not available
- Be precise with ingredient amounts and instruction details
- Do not add any text outside of this template structure"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        image_data,
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        # Extract text from response
        content = message.content[0].text if message.content else ""
        return content
