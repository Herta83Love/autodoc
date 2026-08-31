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

    except Exception:
        pass

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

        except Exception:
            pass

    import asyncio

    await asyncio.sleep(5)  