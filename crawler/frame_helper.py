import asyncio
from time import monotonic


async def get_main_frame(page, timeout_ms=0):
    """Return mainFrame immediately, or briefly poll while it is replaced."""

    deadline = monotonic() + timeout_ms / 1000

    while True:
        for frame in page.frames:
            if frame.name == "mainFrame":
                return frame

        if monotonic() >= deadline:
            return None

        await asyncio.sleep(0.05)
