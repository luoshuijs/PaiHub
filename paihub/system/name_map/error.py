from paihub.error import PaiHubException


class NameMapError(PaiHubException):
    """NameMap 相关错误基类"""


class InvalidRegexError(NameMapError):
    """无效的正则表达式"""
