from pathlib import Path


def ensure_directories():

    Path("output").mkdir(
        exist_ok=True
    )

    Path(
        "output/screenshots"
    ).mkdir(
        parents=True,
        exist_ok=True
    )

    Path(
        "output/html"
    ).mkdir(
        parents=True,
        exist_ok=True
    )
