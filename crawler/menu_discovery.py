# ============================================================================
# File: menu_discovery.py
# ============================================================================

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

        results.append({

            "category": category,

            "title": title,

            "url": url

        })

    #
    # Debug
    #
    print("\n===== MENU =====")

    for item in results:

        print(item)

    print("================\n")
    print(f"Total menu items: {len(results)}")

    return results