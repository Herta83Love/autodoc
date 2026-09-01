# ============================================================================
# File: sitemap.py
# ============================================================================

async def discover_pages(page, config):

    selector = (
        config["crawl"]["menu_selector"]
    )

    links = await page.eval_on_selector_all(
        selector,
        """
        nodes => nodes.map(node => ({
            title: node.innerText,
            href: node.href
        }))
        """
    )

    result = []

    visited = set()

    for item in links:

        href = item["href"]

        if href not in visited:

            visited.add(href)

            result.append(item)

    return result