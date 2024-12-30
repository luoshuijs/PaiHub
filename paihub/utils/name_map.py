import re
from collections.abc import Iterable
from os import PathLike
from pathlib import Path

try:
    import orjson as jsonlib
except ImportError:
    import json as jsonlib


class NameMap:
    def __init__(self, data_file: str | PathLike[str]):
        self.data_file = Path(data_file)
        self.name_map: dict = {}
        self.tag_regex: re.Pattern[str] | None = None
        self.regex_str: str = ""
        self.load()

    def load(self):
        with open(self.data_file, encoding="utf-8") as f:
            self.name_map = jsonlib.loads(f.read())

        regex_patterns = []
        for key, value in self.name_map.items():
            # Construct regex pattern for each character
            pattern_parts = [f"^{n}$" if len(n) < 2 else n for n in value["name"]] + value["regex"]  # noqa: PLR2004
            character_pattern = f"(?P<{key}>{'|'.join(pattern_parts)})"
            regex_patterns.append(character_pattern)

        self.regex_str = f"(?:^{'|'.join(regex_patterns)})"
        self.tag_regex = re.compile(self.regex_str, re.IGNORECASE | re.MULTILINE)

    def filter_character_tags(self, tags: Iterable[str]) -> str:
        characters = self.identify_characters(tags)
        nested_names = self.get_multi_character_names(characters)
        new_tags = tuple(name for names in nested_names for name in names) or tags
        return "#" + " #".join(new_tags) if new_tags else ""

    def identify_characters(self, tags: Iterable[str]) -> set[str]:
        """Identify unique characters from a list of tag strings."""
        characters = set()
        for tag in tags:
            for match in self.tag_regex.finditer(tag):
                characters.update(key for key, value in match.groupdict().items() if value)
        return characters

    def get_character_names(self, character: str) -> tuple[str]:
        """Return character names in the following format ("Kazuha", "枫原万叶")"""
        return tuple(self.name_map.get(character, {}).get("name", ()))

    def get_multi_character_names(self, characters: set[str]) -> set[tuple[str]]:
        """Return character names in the following format: {("Kazuha", "枫原万叶"), ("Klee", "可莉")}"""
        return {self.get_character_names(c) for c in characters if c in self.name_map}
