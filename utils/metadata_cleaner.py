import re


UUID_PATTERN = re.compile(
    r'[a-f0-9]{8}-'
)


BLACKLIST = {

    "",

    "Loading",
    "Loading...",

    "No Data",

    "Close",
    "Apply",
    "Default",
    "Confirm"
}


def is_noise(value):

    if not value:
        return True

    value = value.strip()

    if value in BLACKLIST:
        return True

    if value.startswith("item-"):
        return True

    if UUID_PATTERN.search(
        value
    ):
        return True

    if value.isdigit():
        return True

    if value.startswith(
        "Sort table by"
    ):
        return True

    return False


def clean_items(items):

    results = []

    seen = set()

    for item in items:

        item = item.strip()

        if is_noise(item):
            continue

        if item in seen:
            continue

        seen.add(item)

        results.append(item)

    return results
