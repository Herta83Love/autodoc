#action_extractor.py
from pathlib import Path

ICON_DIR = Path("output/icons")

ICON_DIR.mkdir(
    parents=True,
    exist_ok=True
)
async def extract_actions(frame):

    actions = []

    try:

        buttons = await frame.locator(
            "button"
        ).all()

        for btn in buttons:

            try:

                text = (
                    await btn.text_content()
                    or ""
                ).strip()

                title = (
                    await btn.get_attribute(
                        "title"
                    )
                    or ""
                ).strip()

                aria = (
                    await btn.get_attribute(
                        "aria-label"
                    )
                    or ""
                ).strip()

                icon = ""

                try:

                    icon_node = btn.locator(
                        "i,svg"
                    )

                    if await icon_node.count():

                        icon = (
                            await icon_node.first.get_attribute(
                                "class"
                            )
                            or ""
                        )

                except Exception:
                    pass

                label = (
                    text
                    or title
                    or aria
                )

                if not label and not icon:
                    continue

                safe_name = (label or f"button_{len(actions)}")

                safe_name = (
                    safe_name
                    .replace("/", "_")
                    .replace("\\", "_")
                    .replace(" ", "_")
                )

                image_path = (
                    ICON_DIR
                    /
                    f"{safe_name}.png"
                )

                try:

                    await btn.screenshot(
                        path=str(image_path)
                    )

                    image_file = str(image_path)

                except Exception:

                    image_file = None

                actions.append({
                    "label": label,
                    "icon": icon,
                    "image": image_file
                })

            except Exception:
                pass

    except Exception:
        pass

    return actions
