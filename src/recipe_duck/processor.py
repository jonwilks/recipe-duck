"""Core recipe processing logic."""

import base64
from pathlib import Path
from typing import Any, Optional

from anthropic import Anthropic
from PIL import Image

from recipe_duck.formatter import RecipeFormatter
from recipe_duck.config import FormattingConfig


class RecipeProcessor:
    """Processes recipe images and converts them to markdown."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        template_path: Path | None = None,
        formatting_config: Optional[FormattingConfig] = None,
        apply_formatting: bool = True,
    ):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.template = self._load_template(template_path)
        self.apply_formatting = apply_formatting
        self.formatter = RecipeFormatter(formatting_config) if apply_formatting else None

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

    def process_image(self, image_path: Path, verbose: bool = False) -> str:
        """Process a recipe image and return markdown content.

        Args:
            image_path: Path to the recipe image file
            verbose: Enable verbose logging

        Returns:
            Markdown formatted recipe content
        """
        # Load and encode image
        image_data = self._encode_image(image_path)
        if verbose:
            import sys
            print(f"📊 Encoded image size: {len(image_data['source']['data'])} bytes", file=sys.stderr)

        # Get structured recipe data from Claude
        if verbose:
            import sys
            print(f"🤖 Calling AI model: {self.model}", file=sys.stderr)

        markdown = self._extract_recipe(image_data, verbose=verbose)

        if verbose:
            import sys
            print(f"📄 Raw markdown length: {len(markdown)} characters", file=sys.stderr)

        # Apply deterministic formatting if enabled
        if self.apply_formatting and self.formatter:
            if verbose:
                import sys
                print(f"✨ Applying deterministic formatting...", file=sys.stderr)
            markdown = self.formatter.format(markdown)
            markdown = self.formatter.renumber_instructions(markdown)
            if verbose:
                import sys
                print(f"📄 Formatted markdown length: {len(markdown)} characters", file=sys.stderr)

        return markdown

    def _encode_image(self, image_path: Path) -> dict[str, Any]:
        """Encode image for API submission.

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with image data for API
        """
        # Open and potentially convert image format
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            # Read file bytes directly (no compression)
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

    def _extract_recipe(self, image_data: dict[str, Any], verbose: bool = False) -> str:
        """Extract recipe information using Claude Vision API.

        Args:
            image_data: Encoded image data
            verbose: Enable verbose logging

        Returns:
            Markdown formatted recipe
        """
        prompt = f"""Analyze this recipe image and extract the recipe information into a structured markdown format.

You MUST follow this exact template structure:

{self.template}

Instructions:
- Extract all text accurately from the image, preserving measurements and quantities
- Fill in the template with the actual recipe information
- Use the exact section headers shown in the template including horizontal rules (---)
- For Ingredients: Use bullet points (-) with format "[quantity] [unit] - [preparation/state] - [ingredient name]"
  Examples: "2 cups - finely chopped - onions", "1 tablespoon - melted - butter", "3 ounces - room temperature - cream cheese"
  If no preparation/state is specified, just use: "[quantity] [unit] - [ingredient name]"
- For Instructions: Use numbered lists (1., 2., 3., etc.) with clear, actionable steps
- Add a blank line between each numbered instruction step
- For Photos, Sources, and Notes sections: Only include the heading and horizontal rules. Add content ONLY if clearly visible in the image
- Be precise with ingredient amounts and instruction details
- Do not add any text outside of this template structure
- Include all sections: Ingredients, Instructions, Photos, Sources, and Notes with horizontal rules (---) between them

IMPORTANT FORMATTING GUIDELINES:
- Write out abbreviated units (e.g., "2 tbsp" → "2 tablespoon", "1 tsp" → "1 teaspoon")
- Use ASCII fractions instead of unicode (e.g., "½" → "1/2", "¼" → "1/4")
- Use explicit numbered steps for instructions (1., 2., 3., etc.) with blank lines between steps
- Pluralize units when quantity is greater than 1 (e.g., "2 tablespoons", "3 cups")
- Always include horizontal rules (---) between sections"""

        import time
        start_time = time.time()

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

        elapsed = time.time() - start_time

        if verbose:
            import sys
            print(f"⏱️  API call completed in {elapsed:.2f}s", file=sys.stderr)
            print(f"📊 Input tokens: {message.usage.input_tokens}", file=sys.stderr)
            print(f"📊 Output tokens: {message.usage.output_tokens}", file=sys.stderr)

            # Calculate approximate cost
            if "sonnet" in self.model.lower():
                input_cost = message.usage.input_tokens * 3 / 1_000_000
                output_cost = message.usage.output_tokens * 15 / 1_000_000
            elif "haiku" in self.model.lower():
                input_cost = message.usage.input_tokens * 1 / 1_000_000
                output_cost = message.usage.output_tokens * 5 / 1_000_000
            else:
                input_cost = 0
                output_cost = 0

            total_cost = input_cost + output_cost
            if total_cost > 0:
                print(f"💰 Estimated cost: ${total_cost:.4f}", file=sys.stderr)

        # Extract text from response
        content = message.content[0].text if message.content else ""
        return content
