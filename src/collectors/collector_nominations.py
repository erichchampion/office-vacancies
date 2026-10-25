from playwright.sync_api import sync_playwright
import os
import requests
import pdfplumber
from bs4 import BeautifulSoup
import tempfile
from urllib.parse import urljoin

class NominationCollector:
    def __init__(self, config):
        self.base_url = config["sources"]["nominations"]["base_url"]
        self.keyword = config["sources"]["nominations"]["target_keyword"]

    def collect(self):
        """Orchestrates the collection of candidate data."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.base_url)

            # Look for <a> tags containing the keyword to avoid selecting non-link elements
            links = page.locator(f"a:has-text('{self.keyword}')").all()

            results = []
            for link in links:
                href = link.get_attribute("href")
                if not href: continue

                full_url = urljoin(self.base_url, href)

                if full_url.endswith(".pdf"):
                    results.extend(self._parse_pdf(full_url))
                else:
                    results.extend(self._parse_html(full_url, page))

            browser.close()
            return results

    def _parse_pdf(self, url):
        """Downloads and parses a PDF for candidate tables."""
        try:
            response = requests.get(url, timeout=30)

            # Use a temporary file to avoid hardcoded paths and race conditions
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            data = []
            with pdfplumber.open(tmp_path) as pdf:
                # Parse all pages to avoid missing vacancies in long documents
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        # Assume format: [Office, Seats Open, Candidates Filed, ...]
                        # Skip header if it contains "Office"
                        for row in table:
                            if row and row[0] and "Office" not in row[0]:
                                data.append((row[0], row[1], row[2]))

            os.remove(tmp_path)
            return data
        except Exception as e:
            print(f"PDF Parsing Error ({url}): {e}")
            return []

    def _parse_html(self, url, page):
        """Parses HTML tables for candidate data."""
        try:
            page.goto(url)
            content = page.content()
            soup = BeautifulSoup(content, "html.parser")

            data = []
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 3:
                        text = cols[0].get_text(strip=True)
                        if text and "Office" not in text:
                            data.append((text, cols[1].get_text(strip=True), cols[2].get_text(strip=True)))
            return data
        except Exception as e:
            print(f"HTML Parsing Error ({url}): {e}")
            return []
