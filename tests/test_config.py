"""Tests for formatting configuration."""

from recipe_duck.config import FormattingConfig, DEFAULT_CONFIG


class TestFormattingConfig:
    """Test FormattingConfig dataclass."""

    def test_default_config_exists(self):
        """Test that default config is available."""
        assert DEFAULT_CONFIG is not None
        assert isinstance(DEFAULT_CONFIG, FormattingConfig)

    def test_default_unit_normalizations(self):
        """Test that common unit abbreviations are in default config."""
        assert "tbsp" in DEFAULT_CONFIG.unit_normalizations
        assert DEFAULT_CONFIG.unit_normalizations["tbsp"] == "tablespoon"
        assert "tsp" in DEFAULT_CONFIG.unit_normalizations
        assert DEFAULT_CONFIG.unit_normalizations["tsp"] == "teaspoon"
        assert "oz" in DEFAULT_CONFIG.unit_normalizations
        assert DEFAULT_CONFIG.unit_normalizations["oz"] == "ounce"
        assert "lb" in DEFAULT_CONFIG.unit_normalizations
        assert DEFAULT_CONFIG.unit_normalizations["lb"] == "pound"

    def test_default_fraction_normalizations(self):
        """Test that common fractions are in default config."""
        assert "½" in DEFAULT_CONFIG.fraction_normalizations
        assert DEFAULT_CONFIG.fraction_normalizations["½"] == "1/2"
        assert "¼" in DEFAULT_CONFIG.fraction_normalizations
        assert DEFAULT_CONFIG.fraction_normalizations["¼"] == "1/4"
        assert "¾" in DEFAULT_CONFIG.fraction_normalizations
        assert DEFAULT_CONFIG.fraction_normalizations["¾"] == "3/4"
        assert "0.5" in DEFAULT_CONFIG.fraction_normalizations
        assert DEFAULT_CONFIG.fraction_normalizations["0.5"] == "1/2"

    def test_default_flags(self):
        """Test default boolean flags are set correctly."""
        assert DEFAULT_CONFIG.enforce_numbered_steps is True
        assert DEFAULT_CONFIG.enforce_ingredient_bullets is True
        assert DEFAULT_CONFIG.pluralize_units is True

    def test_default_unit_plurals(self):
        """Test that common plural forms are defined."""
        assert "tablespoon" in DEFAULT_CONFIG.unit_plurals
        assert DEFAULT_CONFIG.unit_plurals["tablespoon"] == "tablespoons"
        assert "cup" in DEFAULT_CONFIG.unit_plurals
        assert DEFAULT_CONFIG.unit_plurals["cup"] == "cups"

    def test_custom_config(self):
        """Test creating a custom config with overrides."""
        custom_config = FormattingConfig(
            unit_normalizations={"T": "Tablespoon"},
            enforce_numbered_steps=False,
        )
        assert custom_config.unit_normalizations == {"T": "Tablespoon"}
        assert custom_config.enforce_numbered_steps is False
        # Other fields should have defaults
        assert custom_config.pluralize_units is True

    def test_config_immutability(self):
        """Test that config can be safely copied/modified."""
        config1 = FormattingConfig()
        config2 = FormattingConfig()

        # Modify one instance
        config1.unit_normalizations["new_unit"] = "new_value"

        # Ensure the other instance is not affected
        assert "new_unit" not in config2.unit_normalizations
