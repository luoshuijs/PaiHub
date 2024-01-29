import re

patterns = [
    # https://pixiv.net/i/123456
    # https://pixiv.net/artworks/123456
    # https://www.pixiv.net/en/artworks/123456
    # https://www.pixiv.net/member_illust.php?mode=medium&illust_id=123456
    r"(?:www\.)?pixiv\.net/(?:en/)?" r"(?:(?:i|artworks)/|member_illust\.php\?(?:mode=[a-z_]*&)?illust_id=)(\d+)",
    # https://i.pximg.net/img-original/img/2020/02/02/20/00/02/123456_p0.png
    # https://i1.pixiv.net/img-original/img/2020/02/02/20/00/02/123456_p0.png
    # https://i-f.pximg.net/img-original/img/2020/02/02/20/00/02/123456_p0.png
    # https://i.pximg.net/img-master/img/2020/02/02/20/00/02/123456_p0_master1200.jpg
    # https://i1.pixiv.net/img-original/img/2020/02/02/20/00/02/123456_ugoira1920x1080.zip
    # https://i.pximg.net/c/540x540_10_webp/img-master/img/2020/02/02/20/00/02/123456_p0_square1200.jpg
    r"[^./]+\.(?:pximg|pixiv)\.net/" r"(?:\w+/)*img-[a-z-]+/img/\d{4}/\d{2}/\d{2}/\d{2}/\d{2}/\d{2}/(\d+)",
    # http://img1.pixiv.net/img/abcdef/123456.jpg
    # http://img1.pixiv.net/img/abcdef/123456_s.jpg
    # http://i1.pixiv.net/img01/img/abcdef/123456.jpg
    # http://i1.pixiv.net/img01/img/abcdef/123456_p0.jpg
    r"(?:i|img)\d+\.pixiv\.net/(?:img\d+/)?img/(?:\S+)*/(\d+)",
]

# 必须预编译表达式 否则性能会下降
compiled_patterns = [re.compile(p) for p in patterns]
