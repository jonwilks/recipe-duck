"""URL extraction module for recipe-duck.

Handles fetching web recipe pages for LLM processing.
"""

import re
import time
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class URLRecipeExtractor:
    """Fetch and clean recipe webpages for LLM extraction."""

    def __init__(self, anthropic_client=None):
        """Initialize the URL extractor with default headers.

        Args:
            anthropic_client: Optional Anthropic client for LLM-based print URL detection
        """
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.anthropic_client = anthropic_client
        self._print_url_cache: dict[str, str] = {}  # Cache successful patterns by domain

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

    def find_best_url(
        self,
        url: str,
        detection_model: Optional[str] = None,
        timeout_budget: int = 15,
        verbose: bool = False,
    ) -> tuple[str, str]:
        """Find the best URL for recipe extraction, preferring print-friendly versions.

        This method uses a hybrid approach:
        1. Check cache for previously successful patterns for this domain
        2. Try common print URL patterns (fast)
        3. If patterns fail, use LLM to analyze page HTML for print button (intelligent fallback)
        4. If all fail, return original URL

        Args:
            url: Original recipe URL
            detection_model: Model to use for LLM-based detection (default: haiku)
            timeout_budget: Maximum time to spend searching (seconds)
            verbose: Enable verbose logging

        Returns:
            Tuple of (best_url, method_used) where method is one of:
            "cache", "pattern", "llm", "original"
        """
        import sys

        start_time = time.time()

        if verbose:
            print(f"[PRINT-URL] Starting search for: {url}", file=sys.stderr)

        try:
            domain = self._get_domain(url)

            # Check cache first
            if domain in self._print_url_cache:
                cached_pattern = self._print_url_cache[domain]
                if verbose:
                    print(f"[PRINT-URL] ✓ Cache hit for domain: {domain} (pattern: {cached_pattern})", file=sys.stderr)

                # Apply cached pattern
                candidate = self._apply_pattern(url, cached_pattern)
                is_valid, content_len = self._validate_print_url(candidate, timeout=5)
                if is_valid:
                    elapsed = time.time() - start_time
                    if verbose:
                        print(f"[PRINT-URL] ✓ Using cached pattern | Time: {elapsed:.2f}s", file=sys.stderr)
                    return candidate, "cache"
                else:
                    # Cache is stale, remove it
                    del self._print_url_cache[domain]
                    if verbose:
                        print(f"[PRINT-URL] Cache miss (stale) for domain: {domain}", file=sys.stderr)

            # Try common patterns
            patterns = self._generate_print_candidates(url)
            for i, candidate in enumerate(patterns, 1):
                if time.time() - start_time > timeout_budget:
                    if verbose:
                        print(f"[PRINT-URL] Timeout budget exceeded, using original URL", file=sys.stderr)
                    return url, "original"

                if verbose:
                    print(f"[PRINT-URL] Trying pattern {i}/{len(patterns)}: {candidate}", file=sys.stderr)

                is_valid, content_len = self._validate_print_url(candidate, timeout=5)
                if is_valid:
                    # Cache this successful pattern
                    pattern_type = self._identify_pattern(candidate, url)
                    self._print_url_cache[domain] = pattern_type

                    elapsed = time.time() - start_time
                    if verbose:
                        print(f"[PRINT-URL] ✓ Pattern match! | Method: pattern | Time: {elapsed:.2f}s", file=sys.stderr)
                        print(f"[PRINT-URL] Using: {candidate}", file=sys.stderr)
                    return candidate, "pattern"

            # Patterns failed, try LLM detection if client available
            if self.anthropic_client and (time.time() - start_time < timeout_budget):
                if verbose:
                    print(f"[PRINT-URL] Patterns failed, trying LLM detection...", file=sys.stderr)

                print_url = self._ask_llm_for_print_url(url, detection_model, verbose=verbose)
                if print_url:
                    elapsed = time.time() - start_time
                    if verbose:
                        print(f"[PRINT-URL] ✓ LLM found print URL | Time: {elapsed:.2f}s", file=sys.stderr)
                        print(f"[PRINT-URL] Using: {print_url}", file=sys.stderr)
                    return print_url, "llm"

            # All methods failed, use original
            elapsed = time.time() - start_time
            if verbose:
                print(f"[PRINT-URL] No print version found | Time: {elapsed:.2f}s | Using original URL", file=sys.stderr)
            return url, "original"

        except Exception as e:
            if verbose:
                print(f"[PRINT-URL] ERROR: {str(e)} - falling back to original URL", file=sys.stderr)
            return url, "original"

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain (e.g., "budgetbytes.com")
        """
        parsed = urlparse(url)
        return parsed.netloc

    def _extract_recipe_slug(self, url: str) -> Optional[str]:
        """Extract recipe slug from URL for WordPress-style patterns.

        Args:
            url: Recipe URL

        Returns:
            Recipe slug or None if not found

        Examples:
            "https://example.com/recipes/chocolate-chip-cookies/" -> "chocolate-chip-cookies"
            "https://example.com/2024/01/my-recipe" -> "my-recipe"
        """
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]

        # Get last meaningful part (skip numeric IDs, years, etc.)
        for part in reversed(path_parts):
            # Must be at least 3 chars and not all digits
            if len(part) >= 3 and not part.isdigit():
                # Clean up trailing extensions
                slug = re.sub(r"\.(html|htm|php)$", "", part)
                return slug

        return None

    def _generate_print_candidates(self, url: str) -> list[str]:
        """Generate candidate print URLs to try.

        Args:
            url: Original recipe URL

        Returns:
            List of candidate URLs in priority order
        """
        candidates = []
        parsed = urlparse(url)
        base_url = url.rstrip("/")

        # Pattern 1: ?print (Serious Eats, many blogs)
        if "?" in url:
            candidates.append(f"{base_url}&print")
        else:
            candidates.append(f"{base_url}?print")

        # Pattern 2: ?printview (Allrecipes)
        if "?" in url:
            candidates.append(f"{base_url}&printview")
        else:
            candidates.append(f"{base_url}?printview")

        # Pattern 3: WordPress Recipe Maker - /wprm_print/slug
        slug = self._extract_recipe_slug(url)
        if slug:
            base = f"{parsed.scheme}://{parsed.netloc}"
            candidates.append(f"{base}/wprm_print/{slug}")

        # Pattern 4: /print/ suffix
        candidates.append(f"{base_url}/print/")

        # Pattern 5: /print suffix (no trailing slash)
        candidates.append(f"{base_url}/print")

        return candidates

    def _apply_pattern(self, url: str, pattern_type: str) -> str:
        """Apply a cached pattern to a URL.

        Args:
            url: Original URL
            pattern_type: Type of pattern to apply

        Returns:
            URL with pattern applied
        """
        base_url = url.rstrip("/")
        parsed = urlparse(url)

        if pattern_type == "query_print":
            return f"{base_url}?print" if "?" not in url else f"{base_url}&print"
        elif pattern_type == "query_printview":
            return f"{base_url}?printview" if "?" not in url else f"{base_url}&printview"
        elif pattern_type == "wprm_print":
            slug = self._extract_recipe_slug(url)
            if slug:
                base = f"{parsed.scheme}://{parsed.netloc}"
                return f"{base}/wprm_print/{slug}"
        elif pattern_type == "suffix_print_slash":
            return f"{base_url}/print/"
        elif pattern_type == "suffix_print":
            return f"{base_url}/print"

        return url

    def _identify_pattern(self, successful_url: str, original_url: str) -> str:
        """Identify which pattern was successful for caching.

        Args:
            successful_url: URL that worked
            original_url: Original URL

        Returns:
            Pattern type string
        """
        # Check more specific patterns first (printview before print)
        if "?printview" in successful_url or "&printview" in successful_url:
            return "query_printview"
        elif "?print" in successful_url or "&print" in successful_url:
            return "query_print"
        elif "/wprm_print/" in successful_url:
            return "wprm_print"
        elif successful_url.endswith("/print/"):
            return "suffix_print_slash"
        elif successful_url.endswith("/print"):
            return "suffix_print"
        return "unknown"

    def _validate_print_url(self, url: str, timeout: int = 5, retry: bool = True) -> tuple[bool, int]:
        """Validate that a print URL exists and returns reasonable content.

        Args:
            url: URL to validate
            timeout: Request timeout in seconds
            retry: Whether to retry on failure

        Returns:
            Tuple of (is_valid, content_length)
        """
        max_retries = 1 if retry else 0

        for attempt in range(max_retries + 1):
            try:
                # Try HEAD request first (faster)
                response = requests.head(url, headers=self.headers, timeout=timeout, allow_redirects=True)

                # Handle rate limiting with exponential backoff
                if response.status_code in (429, 503) and attempt < max_retries:
                    wait_time = 2 ** attempt  # 1s, 2s
                    time.sleep(wait_time)
                    continue

                if response.status_code == 200:
                    # Check content length if available
                    content_length = int(response.headers.get("content-length", 0))

                    # If content-length not in headers, do a GET request
                    if content_length == 0:
                        response = requests.get(url, headers=self.headers, timeout=timeout)
                        content_length = len(response.content)

                    # Validate reasonable size (>1KB, <5MB)
                    if 1024 < content_length < 5 * 1024 * 1024:
                        return True, content_length

                return False, 0

            except (requests.Timeout, requests.ConnectionError) as e:
                # Retry on timeout or connection errors
                if attempt < max_retries:
                    time.sleep(1)  # Short delay before retry
                    continue
                return False, 0
            except requests.RequestException:
                # Don't retry on other request exceptions
                return False, 0

        return False, 0

    def _ask_llm_for_print_url(
        self,
        url: str,
        model: Optional[str] = None,
        verbose: bool = False,
    ) -> Optional[str]:
        """Use LLM to find print URL by analyzing page HTML.

        Args:
            url: Original recipe URL
            model: Model to use (default: claude-3-5-haiku-20241022)
            verbose: Enable verbose logging

        Returns:
            Print URL if found, None otherwise
        """
        import sys

        if not self.anthropic_client:
            return None

        try:
            # Fetch first 10KB of HTML (usually enough to find print button)
            response = requests.get(url, headers=self.headers, timeout=10, stream=True)
            html_snippet = ""
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    html_snippet += chunk
                    if len(html_snippet) >= 10240:  # 10KB
                        break

            prompt = f"""Analyze this HTML snippet from a recipe webpage and find the print button URL.

URL: {url}

HTML snippet (first 10KB):
{html_snippet[:10240]}

Look for:
- Print buttons, links, or icons
- URLs containing "print", "wprm_print", "printview"
- JavaScript onclick handlers that open print pages

If you find a print URL, return ONLY the full URL (starting with http:// or https://).
If the URL is relative (starts with /), convert it to absolute using the original URL's domain.
If no print URL exists, return exactly: NONE

Print URL:"""

            if verbose:
                print(f"[PRINT-URL] Asking LLM to analyze HTML...", file=sys.stderr)

            model_name = model or "claude-3-5-haiku-20241022"
            message = self.anthropic_client.messages.create(
                model=model_name,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )

            result = message.content[0].text.strip()

            if verbose:
                print(f"[PRINT-URL] LLM response: {result}", file=sys.stderr)

            if result == "NONE" or not result.startswith("http"):
                return None

            # Validate the LLM's suggestion
            is_valid, _ = self._validate_print_url(result, timeout=5)
            if is_valid:
                return result

            return None

        except Exception as e:
            if verbose:
                print(f"[PRINT-URL] LLM detection failed: {str(e)}", file=sys.stderr)
            return None
