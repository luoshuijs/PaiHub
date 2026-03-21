import re
from collections.abc import Iterable
from os import PathLike
from pathlib import Path

from paihub.log import logger

try:
    import orjson as jsonlib
except ImportError:
    import json as jsonlib


class NameMap:
    def __init__(self, data_file: str | PathLike[str]):
        self.data_file = Path(data_file)
        self.name_map: dict = {}
        self.simple_matches: dict[str, str] = {}  # 简单字符串映射 (O(1) 查找)
        self.tag_regex: re.Pattern[str] | None = None
        self.regex_str: str = ""
        self.load()

    def load(self):
        """加载配置文件，包含数据验证和错误处理"""
        try:
            # 读取文件
            with open(self.data_file, encoding="utf-8") as f:
                data = jsonlib.loads(f.read())

            # 验证数据格式
            validated_data = {}
            for key, value in data.items():
                # 跳过注释字段
                if key.startswith("_"):
                    continue

                if self._validate_character_data(key, value):
                    validated_data[key] = value
                else:
                    logger.warning(f"Invalid data for character: {key}")

            self.name_map = validated_data
            self._build_patterns()
            logger.info(f"Loaded {len(self.name_map)} character mappings from {self.data_file}")

        except FileNotFoundError:
            logger.error(f"Name map file not found: {self.data_file}")
            if not self.name_map:
                self.name_map = {}
        except jsonlib.JSONDecodeError as e:
            logger.error(f"Invalid JSON in name map file: {e}")
        except Exception as e:
            logger.error(f"Failed to load name map: {e}", exc_info=True)

    def _validate_character_data(self, key: str, data: dict) -> bool:
        """验证单个角色数据"""
        # 检查必要字段
        if not isinstance(data, dict):
            logger.error(f"Character {key}: data must be a dictionary")
            return False

        if not isinstance(data.get("name"), list) or not data["name"]:
            logger.error(f"Character {key}: 'name' field must be a non-empty list")
            return False

        # 验证正则表达式
        for pattern in data.get("regex", []):
            try:
                re.compile(pattern)
            except re.error as e:
                logger.error(f"Character {key}: invalid regex '{pattern}' - {e}")
                return False

        # 验证 aliases（如果存在）
        aliases = data.get("aliases", [])
        if aliases and not isinstance(aliases, list):
            logger.error(f"Character {key}: 'aliases' must be a list")
            return False

        return True

    def _build_patterns(self):
        """分离简单匹配和复杂正则，提高效率"""
        self.simple_matches = {}  # 重置简单匹配字典
        complex_patterns = []  # 需要正则的模式

        for key, value in self.name_map.items():
            # 官方名称用简单匹配
            for name in value["name"]:
                self.simple_matches[name.lower()] = key
                if name != name.lower():  # 保存原始大小写版本
                    self.simple_matches[name] = key

            # 简单别名也用字典匹配
            for alias in value.get("aliases", []):
                self.simple_matches[alias.lower()] = key

            # 只有复杂模式才用正则
            if regex_list := value.get("regex", []):
                # 构建每个角色的正则模式
                pattern_parts = []
                # 如果角色名小于2个字符，使用严格匹配
                for name in value["name"]:
                    if len(name) < 2:
                        pattern_parts.append(f"^{re.escape(name)}$")
                    else:
                        pattern_parts.append(re.escape(name))

                # 添加正则表达式
                pattern_parts.extend(regex_list)

                character_pattern = f"(?P<{key}>{'|'.join(pattern_parts)})"
                complex_patterns.append(character_pattern)

        # 编译正则表达式
        if complex_patterns:
            self.regex_str = f"(?:{'|'.join(complex_patterns)})"
            try:
                self.tag_regex = re.compile(self.regex_str, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                logger.error(f"Failed to compile combined regex: {e}")
                self.tag_regex = None
        else:
            self.tag_regex = None

        logger.debug(
            f"Built patterns: {len(self.simple_matches)} simple matches, {len(complex_patterns)} regex patterns"
        )

    def identify_characters(self, tags: Iterable[str]) -> set[str]:
        """优先使用简单匹配，后备使用正则"""
        characters = set()

        for tag in tags:
            # 先尝试简单匹配（更快）
            if (char := self.simple_matches.get(tag.lower())) or (char := self.simple_matches.get(tag)):
                characters.add(char)
            # 最后尝试正则匹配
            elif self.tag_regex:
                try:
                    for match in self.tag_regex.finditer(tag):
                        characters.update(key for key, value in match.groupdict().items() if value)
                except Exception as e:
                    logger.error(f"Regex matching error for tag '{tag}': {e}")

        return characters

    def filter_character_tags(self, tags: Iterable[str]) -> str:
        """将标签列表转换为格式化的角色标签字符串"""
        try:
            characters = self.identify_characters(tags)
            nested_names = self.get_multi_character_names(characters)
            new_tags = tuple(name for names in nested_names for name in names) or tags
            return "#" + " #".join(new_tags) if new_tags else ""
        except Exception as e:
            logger.error(f"Error filtering character tags: {e}", exc_info=True)
            # 发生错误时返回原始标签
            return "#" + " #".join(tags) if tags else ""

    def get_character_names(self, character: str) -> tuple[str, ...]:
        """Return character names in the following format ("Kazuha", "枫原万叶")"""
        return tuple(self.name_map.get(character, {}).get("name", ()))

    def get_multi_character_names(self, characters: set[str]) -> set[tuple[str, ...]]:
        """Return character names in the following format: {("Kazuha", "枫原万叶"), ("Klee", "可莉")}"""
        return {self.get_character_names(c) for c in characters if c in self.name_map}

    def reload(self):
        """重新加载配置文件"""
        logger.info(f"Reloading name map from {self.data_file}")
        self.load()
