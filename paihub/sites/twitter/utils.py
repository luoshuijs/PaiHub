import re

patterns = [
    # https://twitter.com/i/web/status/1234567890123456789
    # https://twitter.com/abcdefg/status/1234567890123456789
    # https://www.twitter.com/abcdefg/status/1234567890123456789
    # https://mobile.twitter.com/abcdefg/status/1234567890123456789
    r"(?:mobile\.|www\.)?(?:twitter|x)\.com/[^.]+/status/(\d+)"
]

# 必须预编译表达式 否则性能会下降
compiled_patterns = [re.compile(p) for p in patterns]
