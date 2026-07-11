import asyncio
import os
from datetime import datetime
from types import SimpleNamespace

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("BOT_OWNER", "1")

from paihub.command.review import ReviewCommand
from paihub.entities.artwork import ImageType
from paihub.error import ArtWorkNotFoundError
from paihub.jobs.auto_push import AutoPushJob
from paihub.system.review.entities import AutoReviewResult, StatusStatistics
from paihub.system.review.notifications import (
    format_auto_review_reason,
    format_auto_review_summary,
    should_send_auto_review_images,
)


def make_artwork(image_type: ImageType = ImageType.STATIC):
    author = SimpleNamespace(url="https://example.test/users/42", name="Author <Name>")
    return SimpleNamespace(
        title="Title <One>",
        url="https://example.test/artworks/1",
        web_name="Example",
        author=author,
        create_time=datetime(2026, 7, 9, 8, 30),
        image_type=image_type,
    )


def make_auto_review(description: str, status: bool) -> AutoReviewResult:
    return AutoReviewResult(status=status, statistics=StatusStatistics(), description=description)


class FakeMessage:
    def __init__(self):
        self.chat_actions: list[str] = []
        self.text_messages: list[dict] = []
        self.photos: list[dict] = []
        self.videos: list[dict] = []
        self.media_groups: list[dict] = []

    async def reply_chat_action(self, action):
        self.chat_actions.append(action)

    async def reply_text(self, text, **kwargs):
        self.text_messages.append({"text": text, **kwargs})

    async def reply_photo(self, photo, **kwargs):
        self.photos.append({"photo": photo, **kwargs})

    async def reply_video(self, video, **kwargs):
        self.videos.append({"video": video, **kwargs})

    async def reply_media_group(self, media, **kwargs):
        self.media_groups.append({"media": media, **kwargs})


class FakeReviewContext:
    def __init__(self, artwork=None, image_error: Exception | None = None):
        self.review_id = 99
        self.artwork = artwork if artwork is not None else make_artwork()
        self.image_error = image_error
        self.set_review_status_calls: list[tuple] = []

    async def get_artwork(self):
        return self.artwork

    async def format_artwork_tags(self, artwork, filter_character_tags: bool):
        assert artwork is self.artwork
        assert filter_character_tags is True
        return "#tag"

    async def get_artwork_images(self):
        if self.image_error is not None:
            raise self.image_error
        return ["image-1"]

    async def set_review_status(self, *args, **kwargs):
        self.set_review_status_calls.append((args, kwargs))


class FakeOwnerBot:
    def __init__(self):
        self.messages: list[dict] = []
        self.photos: list[dict] = []
        self.videos: list[dict] = []
        self.media_groups: list[dict] = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)

    async def send_photo(self, **kwargs):
        self.photos.append(kwargs)

    async def send_video(self, **kwargs):
        self.videos.append(kwargs)

    async def send_media_group(self, **kwargs):
        self.media_groups.append(kwargs)


def test_author_blacklist_summary_includes_reason_and_review_info_without_images():
    auto_review = make_auto_review("author_blacklist", False)

    summary = format_auto_review_summary(auto_review, make_artwork(), "#tag")

    assert "命中作者黑名单，当前作品已自动拒绝" in summary
    assert "Title Title &lt;One&gt;" in summary
    assert "Tag #tag" in summary
    assert "By <a href='https://example.test/users/42'>Author &lt;Name&gt;</a>" in summary
    assert "At 2026-07-09 08:30" in summary
    assert not should_send_auto_review_images(auto_review)


def test_author_whitelist_summary_uses_same_review_info_and_sends_images():
    auto_review = make_auto_review("author_whitelist", True)

    summary = format_auto_review_summary(auto_review, make_artwork(), "#tag")

    assert "命中作者白名单，当前作品已自动通过" in summary
    assert "Title Title &lt;One&gt;" in summary
    assert "Tag #tag" in summary
    assert "At 2026-07-09 08:30" in summary
    assert should_send_auto_review_images(auto_review)


def test_unknown_auto_review_reason_falls_back_to_status():
    assert format_auto_review_reason(make_auto_review("unknown", True)) == "当前作品已自动通过"
    assert format_auto_review_reason(make_auto_review("unknown", False)) == "当前作品已自动拒绝"


def test_review_command_blacklist_notification_sends_text_only():
    command = ReviewCommand(None, None)
    message = FakeMessage()
    review_context = FakeReviewContext(image_error=AssertionError("images should not be fetched"))

    asyncio.run(
        command._send_auto_review_notification(
            message,
            review_context,
            make_auto_review("author_blacklist", False),
        )
    )

    assert not message.photos
    assert not message.videos
    assert not message.media_groups
    assert len(message.text_messages) == 1
    assert "命中作者黑名单" in message.text_messages[0]["text"]
    assert message.text_messages[0]["reply_markup"] is not None


def test_review_command_whitelist_notification_sends_media_then_progress_text():
    command = ReviewCommand(None, None)
    message = FakeMessage()
    review_context = FakeReviewContext()

    asyncio.run(
        command._send_auto_review_notification(
            message,
            review_context,
            make_auto_review("author_whitelist", True),
        )
    )

    assert len(message.photos) == 1
    assert "命中作者白名单" in message.photos[0]["caption"]
    assert len(message.text_messages) == 1
    assert "正在获取下一个作品" in message.text_messages[0]["text"]
    assert message.text_messages[0]["reply_markup"] is not None


def test_review_command_notification_failure_is_best_effort_only():
    command = ReviewCommand(None, None)
    message = FakeMessage()
    review_context = FakeReviewContext()

    async def raise_artwork_not_found():
        raise ArtWorkNotFoundError

    review_context.get_artwork = raise_artwork_not_found

    asyncio.run(
        command._send_auto_review_notification(
            message,
            review_context,
            make_auto_review("author_whitelist", True),
        )
    )

    assert review_context.set_review_status_calls == []
    assert len(message.text_messages) == 1
    assert "命中作者白名单" in message.text_messages[0]["text"]


def test_auto_push_owner_blacklist_notification_skips_images_and_includes_review_info():
    job = AutoPushJob(None, None, None, None)
    owner_bot = FakeOwnerBot()
    job.application = SimpleNamespace(
        bot=SimpleNamespace(bot=owner_bot),
        settings=SimpleNamespace(bot=SimpleNamespace(owner=123456)),
    )
    review_context = FakeReviewContext(image_error=AssertionError("images should not be fetched"))

    asyncio.run(
        job._send_to_owner(
            review_context,
            make_auto_review("author_blacklist", False),
            review_id=77,
            work_id=88,
            artwork=review_context.artwork,
        )
    )

    assert not owner_bot.photos
    assert not owner_bot.videos
    assert not owner_bot.media_groups
    assert len(owner_bot.messages) == 1
    assert "命中作者黑名单" in owner_bot.messages[0]["text"]
    assert "Review ID: 77 | Work ID: 88" in owner_bot.messages[0]["text"]
