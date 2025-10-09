"""URL extraction module for recipe-duck.

Handles fetching web recipe pages for LLM processing.
"""

import requests
from bs4 import BeautifulSoup


class URLRecipeExtractor:
    """Fetch and clean recipe webpages for LLM extraction."""

    def __init__(self):
        """Initialize the URL extractor with default headers."""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def fetch_page(self, url: str, timeout: int = 10) -> str:
        """Fetch HTML content from URL.

        Args:
            url: The URL to fetch
            timeout: Request timeout in seconds

        Returns:
            HTML content as string

        Raises:
            Exception: If the URL cannot be fetched
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.Timeout:
            raise Exception(f"Website took too long to respond (timeout: {timeout}s)")
        except requests.HTTPError as e:
            raise Exception(f"Website returned error: {e.response.status_code}")
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")

    def extract_content(self, html: str) -> str:
        """Extract clean text content from HTML for LLM processing.

        Args:
            html: HTML content to parse

        Returns:
            Cleaned text content

        Note:
            This method performs minimal preprocessing - removing scripts, styles,
            and navigation elements. The actual recipe extraction is handled by
            the LLM, which can understand recipe content regardless of HTML structure.
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove elements that are never useful for recipes
        for element in soup(["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]):
            element.decompose()

        # Try to find main content area to reduce noise
        # This is just to reduce token usage, not for extraction accuracy
        main_content = soup.find("main") or soup.find("article") or soup.find("body")

        if main_content:
            return main_content.get_text(separator="\n", strip=True)

        return soup.get_text(separator="\n", strip=True)
