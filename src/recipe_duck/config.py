"""Configuration for recipe formatting rules."""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class FormattingConfig:
    """Configuration for deterministic recipe formatting."""

    # Unit normalization rules (abbreviated -> full form)
    unit_normalizations: Dict[str, str] = field(
        default_factory=lambda: {
            # Volume
            "tbsp": "tablespoon",
            "tbs": "tablespoon",
            "T": "tablespoon",
            "tsp": "teaspoon",
            "t": "teaspoon",
            "c": "cup",
            "pt": "pint",
            "qt": "quart",
            "gal": "gallon",
            "fl oz": "fluid ounce",
            "fl. oz": "fluid ounce",
            "ml": "milliliter",
            "l": "liter",
            # Weight
            "oz": "ounce",
            "lb": "pound",
            "lbs": "pound",
            "g": "gram",
            "kg": "kilogram",
            "mg": "milligram",
            # Temperature
            "f": "°F",
            "°f": "°F",
            "c": "°C",
            "°c": "°C",
        }
    )

    # Fraction normalization rules (unicode/decimal -> ASCII fractions)
    fraction_normalizations: Dict[str, str] = field(
        default_factory=lambda: {
            "½": "1/2",
            "⅓": "1/3",
            "⅔": "2/3",
            "¼": "1/4",
            "¾": "3/4",
            "⅕": "1/5",
            "⅖": "2/5",
            "⅗": "3/5",
            "⅘": "4/5",
            "⅙": "1/6",
            "⅚": "5/6",
            "⅐": "1/7",
            "⅛": "1/8",
            "⅜": "3/8",
            "⅝": "5/8",
            "⅞": "7/8",
            "⅑": "1/9",
            "⅒": "1/10",
            # Common decimal to fraction conversions
            "0.5": "1/2",
            "0.33": "1/3",
            "0.67": "2/3",
            "0.25": "1/4",
            "0.75": "3/4",
        }
    )

    # Ensure numbered steps (1., 2., 3., etc.)
    enforce_numbered_steps: bool = True

    # Ensure bullet points for ingredients
    enforce_ingredient_bullets: bool = True

    # Pluralization rules for units when quantity > 1
    pluralize_units: bool = True

    # Common plural forms (singular -> plural)
    unit_plurals: Dict[str, str] = field(
        default_factory=lambda: {
            "tablespoon": "tablespoons",
            "teaspoon": "teaspoons",
            "cup": "cups",
            "pint": "pints",
            "quart": "quarts",
            "gallon": "gallons",
            "fluid ounce": "fluid ounces",
            "ounce": "ounces",
            "pound": "pounds",
            "gram": "grams",
            "kilogram": "kilograms",
            "milliliter": "milliliters",
            "liter": "liters",
            "clove": "cloves",
            "can": "cans",
            "package": "packages",
            "slice": "slices",
            "piece": "pieces",
        }
    )


# Default configuration instance
DEFAULT_CONFIG = FormattingConfig()
