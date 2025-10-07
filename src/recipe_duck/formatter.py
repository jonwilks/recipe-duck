"""Post-processing formatter for deterministic recipe output."""

import re
from fractions import Fraction
from typing import List, Optional

from recipe_duck.config import FormattingConfig, DEFAULT_CONFIG


class RecipeFormatter:
    """Formats recipe markdown with deterministic rules."""

    def __init__(self, config: Optional[FormattingConfig] = None):
        """Initialize formatter with config.

        Args:
            config: Formatting configuration. Uses DEFAULT_CONFIG if None.
        """
        self.config = config or DEFAULT_CONFIG

    def format(self, markdown: str) -> str:
        """Apply all formatting rules to recipe markdown.

        Args:
            markdown: Raw markdown from AI extraction

        Returns:
            Formatted markdown with deterministic rules applied
        """
        # Process line by line to maintain structure
        lines = markdown.split("\n")
        formatted_lines = []
        in_ingredients = False
        in_instructions = False

        for line in lines:
            # Track which section we're in
            if line.strip().startswith("## Ingredients"):
                in_ingredients = True
                in_instructions = False
                formatted_lines.append(line)
                continue
            elif line.strip().startswith("## Instructions"):
                in_ingredients = False
                in_instructions = True
                formatted_lines.append(line)
                continue
            elif line.strip().startswith("##") or line.strip().startswith("#"):
                in_ingredients = False
                in_instructions = False
                formatted_lines.append(line)
                continue

            # Apply section-specific formatting
            if in_ingredients and line.strip():
                formatted_line = self._format_ingredient_line(line)
            elif in_instructions and line.strip():
                formatted_line = self._format_instruction_line(line)
            else:
                formatted_line = line

            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)

    def _format_ingredient_line(self, line: str) -> str:
        """Format an ingredient line with deterministic rules.

        Args:
            line: Single ingredient line

        Returns:
            Formatted ingredient line
        """
        # Ensure bullet point
        stripped = line.lstrip()
        if self.config.enforce_ingredient_bullets and not stripped.startswith("-"):
            # Add bullet if it's not empty and not already bulleted
            if stripped and not stripped.startswith("*"):
                line = "- " + stripped
            elif stripped.startswith("*"):
                # Convert asterisk to dash
                line = "- " + stripped[1:].lstrip()

        # Normalize fractions
        line = self._normalize_fractions(line)

        # Normalize units
        line = self._normalize_units(line)

        return line

    def _format_instruction_line(self, line: str) -> str:
        """Format an instruction line with deterministic rules.

        Args:
            line: Single instruction line

        Returns:
            Formatted instruction line
        """
        # Ensure numbered list format
        stripped = line.lstrip()
        if self.config.enforce_numbered_steps and stripped:
            # Check if it already starts with a number followed by period or )
            if not re.match(r"^\d+[\.\)]\s", stripped):
                # If it starts with a bullet or other marker, remove it
                if stripped.startswith("-") or stripped.startswith("*"):
                    stripped = stripped[1:].lstrip()
                # Don't auto-number yet - that requires context of line position
                # Just ensure clean format for now
                line = stripped
            else:
                line = stripped

        return line

    def _normalize_fractions(self, text: str) -> str:
        """Normalize fractions to ASCII format.

        Args:
            text: Text containing fractions

        Returns:
            Text with normalized fractions
        """
        result = text
        for unicode_frac, ascii_frac in self.config.fraction_normalizations.items():
            result = result.replace(unicode_frac, ascii_frac)
        return result

    def _normalize_units(self, text: str) -> str:
        """Normalize measurement units to full form.

        Args:
            text: Text containing units

        Returns:
            Text with normalized units
        """
        result = text

        # Pattern to match quantity + unit
        # Matches things like "2 tbsp", "1/2 tsp", "3.5 oz", etc.
        pattern = r'\b(\d+(?:[\/\.\d]*)?)\s*(' + '|'.join(
            re.escape(abbr) for abbr in self.config.unit_normalizations.keys()
        ) + r')s?\b'

        def replace_unit(match):
            quantity = match.group(1)
            unit_abbr = match.group(2).lower()

            # Get full unit name
            full_unit = self.config.unit_normalizations.get(
                unit_abbr,
                unit_abbr
            )

            # Handle pluralization if enabled
            if self.config.pluralize_units:
                try:
                    # Parse quantity to determine if plural
                    if '/' in quantity:
                        # Fraction
                        frac = Fraction(quantity)
                        needs_plural = frac > 1
                    else:
                        # Decimal or integer
                        num = float(quantity)
                        needs_plural = num > 1

                    if needs_plural and full_unit in self.config.unit_plurals:
                        full_unit = self.config.unit_plurals[full_unit]
                except (ValueError, ZeroDivisionError):
                    # If we can't parse, keep singular
                    pass

            return f"{quantity} {full_unit}"

        result = re.sub(pattern, replace_unit, result, flags=re.IGNORECASE)
        return result

    def renumber_instructions(self, markdown: str) -> str:
        """Renumber instruction steps to ensure sequential numbering with blank lines between.

        Args:
            markdown: Markdown with potential instruction numbering issues

        Returns:
            Markdown with sequentially numbered instructions and blank lines
        """
        lines = markdown.split("\n")
        result_lines = []
        in_instructions = False
        step_number = 1

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("## Instructions"):
                in_instructions = True
                step_number = 1
                result_lines.append(line)
                continue
            elif stripped.startswith("##") or stripped.startswith("#"):
                in_instructions = False
                result_lines.append(line)
                continue
            elif stripped == "---":
                # Horizontal rules always end the instructions section and pass through
                in_instructions = False
                result_lines.append(line)
                continue

            if in_instructions and stripped:
                # Remove any existing numbering or bullets
                # Match existing number patterns
                content = re.sub(r'^\d+[\.\)]\s*', '', stripped)
                # Also handle dash bullets
                if content.startswith("- "):
                    content = content[2:].strip()

                if content:  # Only number non-empty lines
                    # Add blank line before step if not the first step
                    if step_number > 1:
                        result_lines.append("")
                    result_lines.append(f"{step_number}. {content}")
                    step_number += 1
            else:
                result_lines.append(line)

        return "\n".join(result_lines)
