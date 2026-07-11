import html
from typing import Any

from paihub.system.review.entities import AutoReviewResult

_AUTO_REVIEW_REASONS = {
    "author_whitelist": "命中作者白名单，当前作品已自动通过",
    "author_blacklist": "命中作者黑名单，当前作品已自动拒绝",
    "history_pass_ratio": "根据历史审核记录，当前作品已自动通过",
    "history_reject_ratio": "根据历史审核记录，当前作品已自动拒绝",
}


def format_auto_review_reason(auto_review: AutoReviewResult) -> str:
    if auto_review.description in _AUTO_REVIEW_REASONS:
        return _AUTO_REVIEW_REASONS[auto_review.description]
    if auto_review.status:
        return "当前作品已自动通过"
    return "当前作品已自动拒绝"


def format_review_summary(artwork: Any, formatted_tags: str) -> str:
    return (
        f"Title {html.escape(artwork.title)}\n"
        f"Tag {html.escape(formatted_tags)}\n"
        f"From <a href='{artwork.url}'>{artwork.web_name}</a> "
        f"By <a href='{artwork.author.url}'>{html.escape(artwork.author.name)}</a>\n"
        f"At {artwork.create_time.strftime('%Y-%m-%d %H:%M')}"
    )


def format_auto_review_summary(auto_review: AutoReviewResult, artwork: Any, formatted_tags: str) -> str:
    return f"{format_auto_review_reason(auto_review)}\n{format_review_summary(artwork, formatted_tags)}"


def should_send_auto_review_images(auto_review: AutoReviewResult) -> bool:
    return auto_review.description == "author_whitelist"
