import re

from ..._utils.url import normalize_for_matching
from ._normalization import compile_url_pattern, normalize_pattern_for_storage
from ._validation import pattern_covers


class UrlRegistry:
    """Store full-URL wildcard patterns.

    This registry is meant to be shared between URL-related scanners as a centralized allowed URLs source of truth.

    Args:
        entries (list[str] | None = None): Optional list of full-URL wildcard patterns to initialize the registry.
    """

    def __init__(self, entries: list[str] | None = None) -> None:
        self._patterns: list[tuple[str, re.Pattern[str]]] = []

        for entry in entries or []:
            self.register(entry)

    def register(self, entry: str) -> None:
        """Register a full-URL wildcard pattern.

        Args:
            entry (str): Full-URL wildcard pattern.
        """
        normalized = normalize_pattern_for_storage(entry)
        if not normalized:
            return

        for existing_pattern, _ in self._patterns:
            if pattern_covers(existing_pattern, normalized):
                return

        self._patterns = [
            (existing_pattern, compiled_pattern)
            for existing_pattern, compiled_pattern in self._patterns
            if not pattern_covers(normalized, existing_pattern)
        ]
        self._patterns.append((normalized, compile_url_pattern(normalized)))

    def is_allowed(self, url: str) -> bool:
        """Check whether a URL matches any stored URL rule.

        Args:
            url (str): URL to validate.

        Returns:
            bool: True when the URL matches any stored full-URL pattern; otherwise, False.
        """
        normalized_url = normalize_for_matching(url)
        if normalized_url is None:
            return False

        return any(compiled_pattern.fullmatch(normalized_url) for _, compiled_pattern in self._patterns)
