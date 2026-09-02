# ============================================================================
# File: wait_helper.py
# ============================================================================

import asyncio
import logging


logger = logging.getLogger(__name__)


async def wait_frame_ready(
    frame,
    timeout_ms=30000
):

    try:

        await frame.locator(
            "body"
        ).wait_for(
            state="visible",
            timeout=timeout_ms
        )

    except Exception as exc:
        logger.debug("等待 frame body 顯示失敗：%s", exc)

    previous_len = 0

    for _ in range(10):

        try:

            text = await frame.locator(
                "body"
            ).inner_text()

            current_len = len(text)

            print(
                f"DOM文字數: {current_len}"
            )

            if current_len > 0:

                if abs(
                    current_len - previous_len
                ) < 10:

                    #
                    # 不要再用 page.wait_for_timeout
                    #

                    return

            previous_len = current_len

            #
            # 改用 asyncio.sleep
            #

            import asyncio

            await asyncio.sleep(1)

        except Exception as exc:
            logger.debug("讀取 frame 內容失敗：%s", exc)

    await asyncio.sleep(5)  



async def wait_page_content_change(
    frame,
    before_text,
    timeout=15
):

    for _ in range(timeout * 2):

        try:

            current_text = (
                await frame.locator(
                    "body"
                ).inner_text()
            )

            if (
                current_text
                and current_text != before_text
            ):

                return

        except Exception as exc:
            logger.debug("等待頁面內容變更時讀取失敗：%s", exc)

        await asyncio.sleep(0.5)


async def wait_dom_stable(
    frame,
    stable_rounds=3,
    interval=1
):

    previous = None

    stable_count = 0

    for _ in range(60):

        try:

            current = (
                await frame.locator(
                    "body"
                ).inner_text()
            )

            current = current.strip()

            if current == previous:

                stable_count += 1

            else:

                stable_count = 0

            if stable_count >= stable_rounds:

                print(
                    "✅ DOM 已穩定"
                )

                return

            previous = current

        except Exception as exc:
            logger.debug("等待 DOM 穩定時讀取失敗：%s", exc)

        await asyncio.sleep(
            interval
        )

    print(
        "⚠️ DOM 等待逾時"
    )
