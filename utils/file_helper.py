# ============================================================================
# File: file_helper.py
# ============================================================================

from pathlib import Path


_ASSET_MARKERS = (
    "/screenshots/",
    "/icons/",
    "/detail_flows/",
    "/html/",
    "/ai_cache/",
)


def localize_output_path(path_value, project_root):
    """Map a crawl asset path onto this checkout.

    Metadata stores Windows paths such as ``output\\en\\screenshots\\a.png``.
    On macOS those backslashes are part of the filename, so the picture is
    reported missing even when the file was copied with the project.
    """

    if not isinstance(path_value, str) or not path_value.strip():
        return path_value

    normalized = path_value.replace("\\", "/")
    lowered = normalized.lower()
    if "output/" not in lowered or not any(marker in lowered for marker in _ASSET_MARKERS):
        return path_value

    parts = [part for part in normalized.split("/") if part]
    output_index = next(
        (index for index, part in enumerate(parts) if part.lower() == "output"),
        None,
    )
    if output_index is None:
        return path_value

    return str(Path(project_root).joinpath(*parts[output_index:]))


def localize_output_tree(value, project_root):
    if isinstance(value, dict):
        return {
            key: localize_output_tree(item, project_root)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [localize_output_tree(item, project_root) for item in value]
    return localize_output_path(value, project_root)


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
