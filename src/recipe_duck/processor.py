"""Core recipe processing logic."""

import base64
from pathlib import Path
from typing import Any, Optional

from anthropic import Anthropic
from PIL import Image

# Register HEIF support for iPhone images
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # HEIF support not available

from recipe_duck.formatter import RecipeFormatter
from recipe_duck.config import FormattingConfig
from recipe_duck.url_extractor import URLRecipeExtractor


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
        self.url_extractor = URLRecipeExtractor()

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

    def process(self, input_path: Path | str, verbose: bool = False, debug: bool = False, debug_dir: Path | None = None) -> str:
        """Process a recipe from either an image file or URL.

        Args:
            input_path: Path to image file or URL string
            verbose: Enable verbose logging
            debug: Enable debug mode (shows prompts and responses)
            debug_dir: Directory to write debug files (default: current directory)

        Returns:
            Markdown formatted recipe content
        """
        # Check if input is a URL
        if isinstance(input_path, str) and input_path.startswith(("http://", "https://")):
            return self.process_url(input_path, verbose=verbose, debug=debug, debug_dir=debug_dir)
        else:
            # Convert to Path if string
            if isinstance(input_path, str):
                input_path = Path(input_path)
            return self.process_image(input_path, verbose=verbose, debug=debug, debug_dir=debug_dir)

    def process_url(self, url: str, verbose: bool = False, debug: bool = False, debug_dir: Path | None = None) -> str:
        """Process a recipe from a URL.

        Args:
            url: URL to recipe webpage
            verbose: Enable verbose logging
            debug: Enable debug mode (shows prompts and responses)
            debug_dir: Directory to write debug files (default: current directory)

        Returns:
            Markdown formatted recipe content
        """
        if verbose:
            import sys
            print(f"Fetching recipe from URL: {url}", file=sys.stderr)

        try:
            # Fetch the webpage
            html = self.url_extractor.fetch_page(url)
            if verbose:
                import sys
                print(f"Downloaded {len(html)} bytes of HTML", file=sys.stderr)

            # Extract clean text content
            content = self.url_extractor.extract_content(html)

            # Limit content to prevent token overflow
            # Using 20000 chars (~5000 tokens) to handle longer recipes
            # Claude 3.5 Sonnet has 200k token context, so this is safe
            max_chars = 20000
            original_length = len(content)
            if len(content) > max_chars:
                if verbose or debug:
                    import sys
                    print(
                        f"WARNING: Content too long ({len(content)} chars), truncating to {max_chars}",
                        file=sys.stderr,
                    )
                    print(
                        f"WARNING: Recipe content may be incomplete. Consider using a recipe site with cleaner HTML.",
                        file=sys.stderr,
                    )
                content = content[:max_chars]

            if verbose:
                import sys
                print(f"Extracted content: {len(content)} characters", file=sys.stderr)
                if original_length > max_chars:
                    print(f"Truncated from {original_length} characters", file=sys.stderr)

            # Send to Claude for processing
            if verbose:
                import sys
                print(f"Processing with AI model: {self.model}", file=sys.stderr)

            markdown = self._extract_recipe_from_url(content, url, verbose=verbose, debug=debug, debug_dir=debug_dir)

            if verbose:
                import sys
                print(f"Raw markdown length: {len(markdown)} characters", file=sys.stderr)

            # Apply deterministic formatting if enabled
            if self.apply_formatting and self.formatter:
                if verbose:
                    import sys
                    print(f"Applying deterministic formatting...", file=sys.stderr)
                markdown = self.formatter.format(markdown)
                markdown = self.formatter.renumber_instructions(markdown)
                if verbose:
                    import sys
                    print(f"Formatted markdown length: {len(markdown)} characters", file=sys.stderr)

            return markdown

        except Exception as e:
            raise Exception(f"Failed to process recipe from URL: {str(e)}")

    def process_image(self, image_path: Path, verbose: bool = False, debug: bool = False, debug_dir: Path | None = None) -> str:
        """Process a recipe image and return markdown content.

        Args:
            image_path: Path to the recipe image file
            verbose: Enable verbose logging
            debug: Enable debug mode (shows prompts and responses)
            debug_dir: Directory to write debug files (default: current directory)

        Returns:
            Markdown formatted recipe content
        """
        # Load and encode image
        image_data = self._encode_image(image_path)
        if verbose:
            import sys
            print(f"Encoded image size: {len(image_data['source']['data'])} bytes", file=sys.stderr)

        # Get structured recipe data from Claude
        if verbose:
            import sys
            print(f"Calling AI model: {self.model}", file=sys.stderr)

        markdown = self._extract_recipe(image_data, verbose=verbose, debug=debug, debug_dir=debug_dir)

        if verbose:
            import sys
            print(f"Raw markdown length: {len(markdown)} characters", file=sys.stderr)

        # Apply deterministic formatting if enabled
        if self.apply_formatting and self.formatter:
            if verbose:
                import sys
                print(f"Applying deterministic formatting...", file=sys.stderr)
            markdown = self.formatter.format(markdown)
            markdown = self.formatter.renumber_instructions(markdown)
            if verbose:
                import sys
                print(f"Formatted markdown length: {len(markdown)} characters", file=sys.stderr)

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

    def _extract_recipe(self, image_data: dict[str, Any], verbose: bool = False, debug: bool = False, debug_dir: Path | None = None) -> str:
        """Extract recipe information using Claude Vision API.

        Args:
            image_data: Encoded image data
            verbose: Enable verbose logging
            debug: Enable debug mode (shows prompts and responses)
            debug_dir: Directory to write debug files (default: current directory)

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

CRITICAL - COMPLETENESS VERIFICATION:
For Ingredients:
1. First, locate and count ALL ingredients visible in the image
2. Extract every single ingredient - do not skip any
3. After extraction, verify your ingredient count matches what's visible in the image
4. If the image shows "X ingredients" or has a numbered/bulleted list, ensure you have exactly that many
5. Double-check you haven't missed any ingredients, especially those at the end of lists or in multiple columns

For Instructions:
1. First, locate and count ALL instruction steps visible in the image
2. Extract every single step - do not skip any, especially not the final steps
3. If the image has numbered instructions, preserve the original numbering (don't renumber)
4. After extraction, verify your step count matches what's visible in the image
5. Pay special attention to capture the LAST instruction step - this is commonly missed
6. Include all sub-steps and details from each instruction

IMPORTANT FORMATTING GUIDELINES:
- Write out abbreviated units (e.g., "2 tbsp" → "2 tablespoon", "1 tsp" → "1 teaspoon")
- Use ASCII fractions instead of unicode (e.g., "½" → "1/2", "¼" → "1/4")
- Use explicit numbered steps for instructions (1., 2., 3., etc.) with blank lines between steps
- Pluralize units when quantity is greater than 1 (e.g., "2 tablespoons", "3 cups")
- Always include horizontal rules (---) between sections"""

        if debug:
            import sys
            from pathlib import Path

            # Determine debug directory
            base_dir = debug_dir if debug_dir else Path.cwd()

            # Write prompt to file
            debug_prompt_file = base_dir / "debug_prompt_image.txt"
            with open(debug_prompt_file, "w", encoding="utf-8") as f:
                f.write("="*80 + "\n")
                f.write("DEBUG MODE - IMAGE EXTRACTION - PROMPT\n")
                f.write("="*80 + "\n\n")
                f.write(prompt)
                f.write(f"\n\n{'='*80}\n")
                f.write(f"IMAGE DATA: {len(image_data['source']['data'])} bytes (base64 encoded)\n")
                f.write("="*80 + "\n")

            print(f"Debug: Prompt written to {debug_prompt_file}", file=sys.stderr)

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
                print(f"Estimated cost: ${total_cost:.4f}", file=sys.stderr)

        # Extract text from response
        content = message.content[0].text if message.content else ""

        if debug:
            import sys
            from pathlib import Path

            # Determine debug directory
            base_dir = debug_dir if debug_dir else Path.cwd()

            # Write response to file
            debug_response_file = base_dir / "debug_response_image.txt"
            with open(debug_response_file, "w", encoding="utf-8") as f:
                f.write("="*80 + "\n")
                f.write("DEBUG MODE - IMAGE EXTRACTION - API RESPONSE\n")
                f.write("="*80 + "\n\n")
                f.write(content)
                f.write("\n\n" + "="*80 + "\n")

            print(f"Debug: Response written to {debug_response_file}", file=sys.stderr)

        return content

    def _extract_recipe_from_url(self, content: str, url: str, verbose: bool = False, debug: bool = False, debug_dir: Path | None = None) -> str:
        """Extract recipe from URL content using Claude API.

        Args:
            content: Extracted text content from webpage
            url: Source URL
            verbose: Enable verbose logging
            debug: Enable debug mode (shows prompts and responses)
            debug_dir: Directory to write debug files (default: current directory)

        Returns:
            Markdown formatted recipe
        """
        prompt = f"""Extract the recipe from the following webpage content and format it into a structured markdown format.

Source URL: {url}

Content:
{content}

You MUST follow this exact template structure:

{self.template}

Instructions:
- Extract ONLY recipe information (ignore ads, navigation, comments, related recipes)
- Fill in the template with the actual recipe information
- Use the exact section headers shown in the template including horizontal rules (---)
- For Ingredients: Use bullet points (-) with format "[quantity] [unit] - [preparation/state] - [ingredient name]"
  Examples: "2 cups - finely chopped - onions", "1 tablespoon - melted - butter", "3 ounces - room temperature - cream cheese"
  If no preparation/state is specified, just use: "[quantity] [unit] - [ingredient name]"
- For Instructions: Use numbered lists (1., 2., 3., etc.) with clear, actionable steps
- Add a blank line between each numbered instruction step
- For Photos, Sources, and Notes sections: Only include the heading and horizontal rules. Add content ONLY if present in the extracted content
- Be precise with ingredient amounts and instruction details
- If information is missing, omit that section entirely
- Ensure measurements are clear and complete
- Clean up any formatting issues or typos from source
- Do not add any text outside of this template structure
- Include all sections: Ingredients, Instructions, Photos, Sources, and Notes with horizontal rules (---) between them

CRITICAL - COMPLETENESS VERIFICATION:
For Ingredients:
1. First, locate and count ALL ingredients in the source content's ingredients list
2. Extract every single ingredient - do not skip any
3. After extraction, verify your ingredient count matches the source
4. If the source shows "X ingredients" or has a numbered/bulleted list, ensure you have exactly that many
5. Double-check you haven't missed any ingredients, especially those at the end of lists

For Instructions:
1. First, locate and count ALL instruction steps in the source content
2. Extract every single step - do not skip any, especially not the final steps
3. If the source has numbered instructions, preserve the original numbering (don't renumber)
4. After extraction, verify your step count matches the source
5. Pay special attention to capture the LAST instruction step - this is commonly missed
6. Include all sub-steps and details from each instruction

IMPORTANT FORMATTING GUIDELINES:
- Write out abbreviated units (e.g., "2 tbsp" → "2 tablespoon", "1 tsp" → "1 teaspoon")
- Use ASCII fractions instead of unicode (e.g., "½" → "1/2", "¼" → "1/4")
- Use explicit numbered steps for instructions (1., 2., 3., etc.) with blank lines between steps
- Pluralize units when quantity is greater than 1 (e.g., "2 tablespoons", "3 cups")
- Always include horizontal rules (---) between sections"""

        if debug:
            import sys
            from pathlib import Path

            # Determine debug directory
            base_dir = debug_dir if debug_dir else Path.cwd()

            # Write prompt to file (includes the extracted webpage content)
            debug_prompt_file = base_dir / "debug_prompt_url.txt"
            with open(debug_prompt_file, "w", encoding="utf-8") as f:
                f.write("="*80 + "\n")
                f.write("DEBUG MODE - URL EXTRACTION - PROMPT\n")
                f.write("="*80 + "\n\n")
                f.write(prompt)
                f.write("\n\n" + "="*80 + "\n")

            print(f"Debug: Prompt (including extracted webpage content) written to {debug_prompt_file}", file=sys.stderr)

        import time

        start_time = time.time()

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        elapsed = time.time() - start_time

        if verbose:
            import sys

            print(f"API call completed in {elapsed:.2f}s", file=sys.stderr)
            print(f"Input tokens: {message.usage.input_tokens}", file=sys.stderr)
            print(f"Output tokens: {message.usage.output_tokens}", file=sys.stderr)

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
                print(f"Estimated cost: ${total_cost:.4f}", file=sys.stderr)

        # Extract text from response
        content = message.content[0].text if message.content else ""

        if debug:
            import sys
            from pathlib import Path

            # Determine debug directory
            base_dir = debug_dir if debug_dir else Path.cwd()

            # Write response to file
            debug_response_file = base_dir / "debug_response_url.txt"
            with open(debug_response_file, "w", encoding="utf-8") as f:
                f.write("="*80 + "\n")
                f.write("DEBUG MODE - URL EXTRACTION - API RESPONSE\n")
                f.write("="*80 + "\n\n")
                f.write(content)
                f.write("\n\n" + "="*80 + "\n")

            print(f"Debug: Response written to {debug_response_file}", file=sys.stderr)

        return content
