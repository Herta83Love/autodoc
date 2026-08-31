async def discover_menu_links(page):

    menu_items = await page.evaluate("""
    () => {

        const results = [];

        const groups = document.querySelectorAll(
            '.side-wrapper'
        );

        groups.forEach(group => {

            const categoryElement =
                group.querySelector(
                    '.side-title'
                );

            const category =
                categoryElement
                    ? categoryElement.innerText.trim()
                    : 'Unknown';

            const menus =
                group.querySelectorAll(
                    '.menu-item'
                );

            menus.forEach(menu => {

                results.push({

                    category: category,

                    title: (
                        menu.innerText || ''
                    ).trim(),

                    url: (
                        menu.href || ''
                    ).trim()

                });

            });

        });

        return results;

    }
    """)

    results = []

    visited = set()

    for item in menu_items:

        category = (
            item.get(
                "category",
                "Unknown"
            )
            .strip()
        )

        title = (
            item.get(
                "title",
                ""
            )
            .strip()
        )

        url = (
            item.get(
                "url",
                ""
            )
            .strip()
        )

        if not title:
            continue

        if not url:
            continue

        if url in visited:
            continue

        visited.add(url)

        results.append({

            "category": category,

            "title": title,

            "url": url

        })

    return results