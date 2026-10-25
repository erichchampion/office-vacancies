from playwright.sync_api import sync_playwright
import re
from urllib.parse import urljoin

class NoticeCollector:
    def __init__(self, config):
        self.sources = config["sources"]["notices"]

    def collect(self):
        """Crawls official notice pages for vacancy keywords."""
        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            for source in self.sources:
                try:
                    page.goto(source["url"])
                    # Get all links
                    links = page.locator("a").all()

                    for link in links:
                        text = link.inner_text()
                        href = link.get_attribute("href")
                        if not href: continue

                        # Check if link text or parent text matches any pattern
                        if any(re.search(pattern, text, re.IGNORECASE) for pattern in source["patterns"]):
                            full_url = urljoin(source["url"], href)
                            results.append({
                                "office": "General Vacancy Notice",
                                "link": full_url,
                                "text": text,
                                "tier": "Tier 3" # Notices are usually specific
                            })
                except Exception as e:
                    print(f"Notice Crawl Error ({source['url']}): {e}")

            browser.close()
        return results
