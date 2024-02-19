import re

patterns = [
    # https://danbooru.donmai.us/posts/123456
    # https://safebooru.donmai.us/posts/123456
    r"(?:danbooru|safebooru)\.donmai\.us/post(?:s|/show)/(?P<id>\d+)",
]

# 必须预编译表达式 否则性能会下降
compiled_patterns = [re.compile(p) for p in patterns]
