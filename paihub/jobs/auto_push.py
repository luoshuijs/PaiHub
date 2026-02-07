import asyncio
import html
from datetime import datetime, timedelta

from apscheduler.triggers.interval import IntervalTrigger
from croniter import CroniterBadCronError, croniter
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.error import RetryAfter as BotRetryAfter

from paihub.base import Job
from paihub.entities.artwork import ImageType
from paihub.error import ArtWorkNotFoundError
from paihub.log import Logger, logger
from paihub.system.push.auto_push_entities import AutoPushMode
from paihub.system.push.auto_push_repositories import AutoPushConfigRepository
from paihub.system.push.services import PushService
from paihub.system.review.entities import ReviewStatus
from paihub.system.review.services import ReviewService
from paihub.system.work.error import WorkRuleNotFound
from paihub.system.work.repositories import WorkChannelRepository

_logger = Logger("Auto Push Job", filename="auto_push.log")  # 详细日志
_main_logger = logger  # 主日志，用于关键信息


class AutoPushJob(Job):
    """自动推送Job - 定时执行自动审核和推送"""

    def __init__(
        self,
        config_repository: AutoPushConfigRepository,
        review_service: ReviewService,
        push_service: PushService,
        work_channel_repository: WorkChannelRepository,
    ):
        self.config_repository = config_repository
        self.review_service = review_service
        self.push_service = push_service
        self.work_channel_repository = work_channel_repository
        self._running_jobs: set[int] = set()  # 记录正在运行的任务ID，防止重复执行

    def add_jobs(self) -> None:
        """添加定时任务"""
        # 每分钟检查一次是否有需要执行的自动推送任务
        self.application.scheduler.add_job(
            self.check_and_run_tasks,
            IntervalTrigger(minutes=1),
            next_run_time=datetime.now() + timedelta(seconds=30),
        )
        _main_logger.info("自动推送Job已启动，将每分钟检查一次待执行任务")
        _logger.info("自动推送Job已启动，将每分钟检查一次待执行任务")

    async def check_and_run_tasks(self):
        """检查并运行待执行的自动推送任务"""
        try:
            enabled_configs = await self.config_repository.get_enabled_configs()
            now = datetime.now()

            for config in enabled_configs:
                # 跳过正在运行的任务
                if config.id in self._running_jobs:
                    continue

                # 检查是否到达执行时间
                if config.next_run_time and config.next_run_time <= now:
                    _main_logger.info("开始执行自动推送任务: %s (ID: %s)", config.name, config.id)
                    _logger.info("开始执行自动推送任务: %s (ID: %s)", config.name, config.id)
                    # 异步执行任务，避免阻塞
                    asyncio.create_task(self.execute_auto_push_task(config))
        except Exception as exc:
            logger.error("检查自动推送任务时发生错误", exc_info=exc)

    async def execute_auto_push_task(self, config):
        """执行自动推送任务
        :param config: AutoPushConfig 配置对象
        """
        config_id = config.id
        try:
            # 标记任务为运行中
            self._running_jobs.add(config_id)
            config.set_running()
            await self.config_repository.update(config)

            _logger.info("执行自动推送任务: %s (Work ID: %s, Mode: %s)", config.name, config.work_id, config.mode.name)

            # 根据模式执行不同的推送逻辑
            if config.mode == AutoPushMode.BATCH:
                await self._execute_batch_mode(config)
            elif config.mode == AutoPushMode.IMMEDIATE:
                await self._execute_immediate_mode(config)

            # 更新下次运行时间
            config.set_completed()
            # 如果是仅运行一次的配置，执行完成后自动禁用
            if config.run_once:
                config.disable(update_by=0)
                _logger.info("配置 '%s' 设置为仅运行一次，已自动禁用", config.name)
            else:
                try:
                    config.next_run_time = self._calculate_next_run_time(config.cron_expression)
                except CroniterBadCronError as exc:
                    logger.error("表达式解析错误 任务将被禁用", exc_info=exc)
                    config.disable(update_by=0)
            await self.config_repository.update(config)

            _main_logger.info("自动推送任务执行完成: %s", config.name)
            _logger.info("自动推送任务执行完成: %s", config.name)
        except Exception as exc:
            _main_logger.error("执行自动推送任务时发生错误: %s", config.name, exc_info=exc)
            logger.error("执行自动推送任务时发生错误: %s", config.name, exc_info=exc)
            # 恢复状态为启用
            config.set_completed()
            await self.config_repository.update(config)
        finally:
            # 移除运行标记
            self._running_jobs.discard(config_id)

    async def _execute_batch_mode(self, config):
        """执行批量模式的自动推送
        :param config: AutoPushConfig 配置对象
        """
        _main_logger.info("批量模式: 开始自动审核 %s 个作品 (Work ID: %s)", config.review_count, config.work_id)
        _logger.info("批量模式: 开始自动审核 %s 个作品", config.review_count)

        # 1. 初始化审核队列
        try:
            await self.review_service.initialize_review_form_sites(
                work_id=config.work_id, lines_per_page=10000, create_by=config.create_by
            )
        except WorkRuleNotFound:
            _main_logger.warning("Work ID %s 未配置规则，跳过任务", config.work_id)
            _logger.warning("Work ID %s 未配置规则，跳过任务", config.work_id)
            return

        count = await self.review_service.initialize_review_queue(work_id=config.work_id)
        _logger.info("审核队列初始化完成，共 %s 个待审核作品", count)

        if count == 0:
            _logger.info("没有待审核作品，跳过任务")
            return

        # 2. 自动审核指定数量的作品
        passed_count = 0
        rejected_count = 0
        passed_reviews = []  # 存储通过审核的review_id

        # 继续审核直到达到目标数量（通过+拒绝），跳过的不计数
        while (passed_count + rejected_count) < config.review_count:
            review_context = await self.review_service.retrieve_next_for_review(work_id=config.work_id)
            if review_context is None:
                _logger.info("审核队列已空，实际处理 %d 个作品", passed_count + rejected_count)
                break

            try:
                auto_review = await review_context.try_auto_review()
                if auto_review is not None and auto_review.status:
                    # 获取作品信息
                    artwork = await review_context.get_artwork()
                    artwork_images = await review_context.get_artwork_images()

                    # 同步到BOT_OWNER
                    if config.push_to_owner:
                        await self._send_to_owner(artwork, artwork_images, review_context.review_id, config.work_id)

                    # 设置审核状态为通过
                    await review_context.set_review_status(
                        ReviewStatus.PASS, auto=True, update_by=config.create_by or 0
                    )
                    passed_reviews.append(review_context.review_id)
                    passed_count += 1
                    _logger.info(
                        "作品自动通过 [%d/%d]: %s[%s]",
                        passed_count + rejected_count,
                        config.review_count,
                        review_context.site_key,
                        review_context.artwork_id,
                    )
                    await asyncio.sleep(2)  # 避免速率限制
                elif auto_review is not None:
                    # 自动拒绝
                    # 获取作品信息（用于发送给 BOT_OWNER）
                    artwork = await review_context.get_artwork()
                    artwork_images = await review_context.get_artwork_images()

                    # 同步到BOT_OWNER（标记为拒绝）
                    if config.push_to_owner:
                        await self._send_to_owner(
                            artwork, artwork_images, review_context.review_id, config.work_id, rejected=True
                        )

                    await review_context.set_review_status(
                        ReviewStatus.REJECT, auto=True, update_by=config.create_by or 0
                    )
                    rejected_count += 1
                    _logger.info(
                        "作品自动拒绝 [%d/%d]: %s[%s]",
                        passed_count + rejected_count,
                        config.review_count,
                        review_context.site_key,
                        review_context.artwork_id,
                    )
                    await asyncio.sleep(2)  # 避免速率限制
                else:
                    # 无法自动审核（返回 None），跳过，不计入统计，继续下一个
                    _logger.debug("作品无法自动审核，跳过: %s[%s]", review_context.site_key, review_context.artwork_id)
            except ArtWorkNotFoundError:
                await review_context.set_review_status(ReviewStatus.NOT_FOUND, update_by=config.create_by or 0)
                _logger.warning("作品不存在: %s[%s]", review_context.site_key, review_context.artwork_id)
            except Exception as exc:
                await review_context.set_review_status(ReviewStatus.ERROR, update_by=config.create_by or 0)
                _logger.error("审核作品时发生错误", exc_info=exc)

        _main_logger.info("批量模式: 完成自动审核，通过 %d 个，拒绝 %d 个", passed_count, rejected_count)
        _logger.info("批量模式: 完成自动审核，通过 %d 个，拒绝 %d 个", passed_count, rejected_count)

        # 3. 统一推送所有通过审核的作品
        if passed_reviews:
            _main_logger.info("批量模式: 开始推送 %s 个作品", len(passed_reviews))
            _logger.info("批量模式: 开始推送 %s 个作品", len(passed_reviews))
            await self._batch_push_artworks(config.work_id, passed_reviews, config.create_by or 0)

    async def _execute_immediate_mode(self, config):
        """执行即时模式的自动推送
        :param config: AutoPushConfig 配置对象
        """
        _main_logger.info("即时模式: 开始自动审核并推送 %s 个作品 (Work ID: %s)", config.review_count, config.work_id)
        _logger.info("即时模式: 开始自动审核并推送 %s 个作品", config.review_count)

        # 1. 初始化审核队列
        try:
            await self.review_service.initialize_review_form_sites(
                work_id=config.work_id, lines_per_page=10000, create_by=config.create_by
            )
        except WorkRuleNotFound:
            _main_logger.warning("Work ID %s 未配置规则，跳过任务", config.work_id)
            _logger.warning("Work ID %s 未配置规则，跳过任务", config.work_id)
            return

        count = await self.review_service.initialize_review_queue(work_id=config.work_id)
        _logger.info("审核队列初始化完成，共 %s 个待审核作品", count)

        if count == 0:
            _logger.info("没有待审核作品，跳过任务")
            return

        # 2. 审核并立即推送
        passed_count = 0
        rejected_count = 0
        work_channel = await self.work_channel_repository.get_by_work_id(config.work_id)

        # 继续审核直到达到目标数量（通过+拒绝），跳过的不计数
        while (passed_count + rejected_count) < config.review_count:
            review_context = await self.review_service.retrieve_next_for_review(work_id=config.work_id)
            if review_context is None:
                _logger.info("审核队列已空，实际处理 %d 个作品", passed_count + rejected_count)
                break

            try:
                auto_review = await review_context.try_auto_review()
                if auto_review is not None and auto_review.status:
                    # 获取作品信息
                    artwork = await review_context.get_artwork()
                    artwork_images = await review_context.get_artwork_images()

                    # 同步到BOT_OWNER
                    if config.push_to_owner:
                        await self._send_to_owner(artwork, artwork_images, review_context.review_id, config.work_id)

                    # 设置审核状态为通过
                    await review_context.set_review_status(
                        ReviewStatus.PASS, auto=True, update_by=config.create_by or 0
                    )

                    # 推送前再次验证状态（防止在极短时间窗口内被 reset_review 修改）
                    review = await self.review_service.get_by_review_id(review_context.review_id)
                    if review and review.status == ReviewStatus.PASS:
                        # 立即推送到频道
                        await self._push_single_artwork(
                            artwork,
                            artwork_images,
                            work_channel.channel_id,
                            review_context.review_id,
                            config.create_by or 0,
                        )

                        passed_count += 1
                        _logger.info(
                            "作品自动通过并推送 [%d/%d]: %s[%s]",
                            passed_count + rejected_count,
                            config.review_count,
                            review_context.site_key,
                            review_context.artwork_id,
                        )
                    else:
                        # 如果状态被修改，仍然计入拒绝数（因为已经处理过）
                        rejected_count += 1
                        _logger.warning(
                            "Review ID %s 状态已被修改为 %s，跳过推送 [%d/%d]",
                            review_context.review_id,
                            review.status.name if review else "NOT_FOUND",
                            passed_count + rejected_count,
                            config.review_count,
                        )
                elif auto_review is not None:
                    # 自动拒绝
                    # 获取作品信息（用于发送给 BOT_OWNER）
                    artwork = await review_context.get_artwork()
                    artwork_images = await review_context.get_artwork_images()

                    # 同步到BOT_OWNER（标记为拒绝）
                    if config.push_to_owner:
                        await self._send_to_owner(
                            artwork, artwork_images, review_context.review_id, config.work_id, rejected=True
                        )

                    await review_context.set_review_status(
                        ReviewStatus.REJECT, auto=True, update_by=config.create_by or 0
                    )
                    rejected_count += 1
                    _logger.info(
                        "作品自动拒绝 [%d/%d]: %s[%s]",
                        passed_count + rejected_count,
                        config.review_count,
                        review_context.site_key,
                        review_context.artwork_id,
                    )
                else:
                    # 无法自动审核（返回 None），跳过，不计入统计，继续下一个
                    _logger.debug("作品无法自动审核，跳过: %s[%s]", review_context.site_key, review_context.artwork_id)
            except ArtWorkNotFoundError:
                await review_context.set_review_status(ReviewStatus.NOT_FOUND, update_by=config.create_by or 0)
                _logger.warning("作品不存在: %s[%s]", review_context.site_key, review_context.artwork_id)
            except BotRetryAfter as exc:
                _logger.warning("触发Telegram速率限制，等待 %s 秒", exc.retry_after)
                await asyncio.sleep(exc.retry_after + 1)
            except Exception as exc:
                await review_context.set_review_status(ReviewStatus.ERROR, update_by=config.create_by or 0)
                _logger.error("审核或推送作品时发生错误", exc_info=exc)

            await asyncio.sleep(3)  # 避免速率限制

        _main_logger.info("即时模式: 完成自动审核并推送，通过 %d 个，拒绝 %d 个", passed_count, rejected_count)
        _logger.info("即时模式: 完成自动审核并推送，通过 %d 个，拒绝 %d 个", passed_count, rejected_count)

    async def _send_to_owner(self, artwork, artwork_images, review_id: int, work_id: int, rejected: bool = False):
        """发送作品到BOT_OWNER
        :param artwork: 作品对象
        :param artwork_images: 作品图片列表
        :param review_id: 审核ID
        :param work_id: 工作ID
        :param rejected: 是否为拒绝的作品
        """
        try:
            bot = self.application.bot.bot  # 获取真正的 Bot 对象
            owner_id = self.application.settings.bot.owner

            status_text = "自动审核拒绝" if rejected else "自动审核通过"
            caption = (
                f"[{status_text}]\n"
                f"Title: {html.escape(artwork.title)}\n"
                f"Tag: {html.escape(artwork.format_tags(filter_character_tags=True))}\n"
                f"From <a href='{artwork.url}'>{artwork.web_name}</a> "
                f"By <a href='{artwork.author.url}'>{html.escape(artwork.author.name)}</a>\n"
                f"Review ID: {review_id} | Work ID: {work_id}"
            )

            if len(artwork_images) > 1:
                media = [InputMediaPhoto(media=artwork_images[0], caption=caption, parse_mode=ParseMode.HTML)]
                media.extend(InputMediaPhoto(media=data) for data in artwork_images[1:])
                media = media[:10]
                await bot.send_media_group(
                    chat_id=owner_id, media=media, connect_timeout=10, read_timeout=10, write_timeout=30
                )
            elif len(artwork_images) == 1:
                if artwork.image_type == ImageType.STATIC:
                    await bot.send_photo(
                        chat_id=owner_id,
                        photo=artwork_images[0],
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        connect_timeout=10,
                        read_timeout=10,
                        write_timeout=30,
                    )
                elif artwork.image_type == ImageType.DYNAMIC:
                    await bot.send_video(
                        chat_id=owner_id,
                        video=artwork_images[0],
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        connect_timeout=10,
                        read_timeout=10,
                        write_timeout=30,
                    )

            # 发送撤销按钮
            keyboard = [
                [
                    InlineKeyboardButton(
                        text="撤销该修改",
                        callback_data=f"reset_review_form_command|{review_id}",
                    ),
                ]
            ]

            message_text = f"当前作品已经{status_text}\n正在获取下一个作品"
            await bot.send_message(
                chat_id=owner_id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
        except Exception as exc:
            _logger.error("发送到BOT_OWNER时发生错误", exc_info=exc)

    async def _push_single_artwork(self, artwork, artwork_images, channel_id: int, review_id: int, create_by: int):
        """推送单个作品到频道
        :param artwork: 作品对象
        :param artwork_images: 作品图片列表
        :param channel_id: 频道ID
        :param review_id: 审核ID
        :param create_by: 创建人ID
        """
        try:
            bot = self.application.bot.bot  # 获取真正的 Bot 对象
            caption = (
                f"Title: {html.escape(artwork.title)}\n"
                f"Tag: {html.escape(artwork.format_tags(filter_character_tags=True))}\n"
                f"From <a href='{artwork.url}'>{artwork.web_name}</a> "
                f"By <a href='{artwork.author.url}'>{html.escape(artwork.author.name)}</a>"
            )

            message_id = None
            if len(artwork_images) > 1:
                media = [InputMediaPhoto(media=artwork_images[0], caption=caption, parse_mode=ParseMode.HTML)]
                media.extend(InputMediaPhoto(media=data) for data in artwork_images[1:])
                media = media[:10]
                messages = await bot.send_media_group(
                    chat_id=channel_id, media=media, connect_timeout=10, read_timeout=10, write_timeout=30
                )
                message_id = messages[0].id
            elif len(artwork_images) == 1:
                if artwork.image_type == ImageType.STATIC:
                    msg = await bot.send_photo(
                        chat_id=channel_id,
                        photo=artwork_images[0],
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        connect_timeout=10,
                        read_timeout=10,
                        write_timeout=30,
                    )
                    message_id = msg.id
                elif artwork.image_type == ImageType.DYNAMIC:
                    msg = await bot.send_video(
                        chat_id=channel_id,
                        video=artwork_images[0],
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        connect_timeout=10,
                        read_timeout=10,
                        write_timeout=30,
                    )
                    message_id = msg.id

            # 记录推送信息
            if message_id:
                await self.push_service.set_send_push(
                    review_id=review_id, channel_id=channel_id, message_id=message_id, status=True, create_by=create_by
                )
        except Exception:
            # 记录推送失败
            await self.push_service.set_send_push(
                review_id=review_id, channel_id=channel_id, message_id=0, status=False, create_by=create_by
            )
            raise

    async def _batch_push_artworks(self, work_id: int, review_ids: list[int], create_by: int):
        """批量推送作品到频道
        :param work_id: 工作ID
        :param review_ids: 审核ID列表
        :param create_by: 创建人ID
        """
        if not review_ids:
            _logger.warning("没有需要推送的作品")
            return

        work_channel = await self.work_channel_repository.get_by_work_id(work_id)

        # 将通过审核的作品添加到推送队列
        await self.push_service.push_cache.set_pending_push(work_id, review_ids)
        _logger.info("已将 %s 个作品添加到推送队列", len(review_ids))

        # 逐个推送
        success_count = 0
        failed_count = 0
        for _ in range(len(review_ids)):
            push_context = await self.push_service.get_next_push_with_validation(work_id=work_id)
            if push_context is None:
                _logger.warning("推送队列为空，跳过")
                break

            try:
                artwork = await push_context.get_artwork()
                artwork_images = await push_context.get_artwork_images()

                await self._push_single_artwork(
                    artwork, artwork_images, work_channel.channel_id, push_context.review_id, create_by
                )
                success_count += 1
                _logger.info("作品推送成功: Review ID %s", push_context.review_id)
            except BotRetryAfter as exc:
                await push_context.undo_push()
                failed_count += 1
                _logger.warning("触发Telegram速率限制，等待 %s 秒", exc.retry_after)
                await asyncio.sleep(exc.retry_after + 1)
            except Exception as exc:
                failed_count += 1
                _logger.error("推送作品时发生错误: Review ID %s", push_context.review_id, exc_info=exc)

            await asyncio.sleep(3)  # 避免速率限制

        _main_logger.info("批量推送完成: 成功 %d 个，失败 %d 个", success_count, failed_count)
        _logger.info("批量推送完成: 成功 %d 个，失败 %d 个", success_count, failed_count)

    @staticmethod
    def _calculate_next_run_time(cron_expression: str) -> datetime:
        """根据cron表达式计算下次运行时间
        :param cron_expression: Cron表达式
        :return: 下次运行时间
        """
        cron = croniter(cron_expression, datetime.now())
        return cron.get_next(datetime)
