import json
import tempfile
from pathlib import Path

import pytest

from paihub.system.name_map.utils import NameMap

SAMPLE_DATA = {
    "Linnea": {
        "name": ["Linnea", "莉奈娅"],
        "regex": [],
        "aliases": ["リンネア"],
    },
    "Kazuha": {
        "name": ["Kazuha", "枫原万叶"],
        "regex": ["万叶"],
        "aliases": ["かずは"],
    },
}


@pytest.fixture()
def name_map(tmp_path: Path) -> NameMap:
    f = tmp_path / "test.json"
    f.write_text(json.dumps(SAMPLE_DATA), encoding="utf-8")
    return NameMap(f)


class TestIdentifyCharacters:
    """identify_characters 的各种匹配场景"""

    def test_exact_name(self, name_map: NameMap):
        assert name_map.identify_characters(["Linnea"]) == {"Linnea"}

    def test_exact_name_chinese(self, name_map: NameMap):
        assert name_map.identify_characters(["莉奈娅"]) == {"Linnea"}

    def test_exact_alias(self, name_map: NameMap):
        assert name_map.identify_characters(["リンネア"]) == {"Linnea"}

    def test_alias_with_suffix(self, name_map: NameMap):
        """核心 bug: リンネア(原神) 应该匹配到 Linnea"""
        assert name_map.identify_characters(["リンネア(原神)"]) == {"Linnea"}

    def test_name_with_suffix(self, name_map: NameMap):
        """名字带后缀也应该匹配"""
        assert name_map.identify_characters(["Linnea(Genshin)"]) == {"Linnea"}

    def test_regex_match(self, name_map: NameMap):
        assert name_map.identify_characters(["万叶"]) == {"Kazuha"}

    def test_no_match(self, name_map: NameMap):
        assert name_map.identify_characters(["原神", "GenshinImpact"]) == set()

    def test_multiple_characters(self, name_map: NameMap):
        result = name_map.identify_characters(["Linnea", "Kazuha"])
        assert result == {"Linnea", "Kazuha"}


class TestFilterCharacterTags:
    """filter_character_tags 端到端测试"""

    def test_real_scenario_linnea(self, name_map: NameMap):
        """复现实际 bug: 原Tag #原神 #GenshinImpact #リンネア(原神)"""
        tags = ["原神", "GenshinImpact", "リンネア(原神)"]
        result = name_map.filter_character_tags(tags)
        assert "Linnea" in result
        assert "莉奈娅" in result

    def test_exact_alias_tag(self, name_map: NameMap):
        tags = ["リンネア"]
        result = name_map.filter_character_tags(tags)
        assert "Linnea" in result
        assert "莉奈娅" in result

    def test_no_character_returns_original(self, name_map: NameMap):
        tags = ["原神", "GenshinImpact"]
        result = name_map.filter_character_tags(tags)
        assert "原神" in result
        assert "GenshinImpact" in result
