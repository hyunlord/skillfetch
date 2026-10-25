# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.50"]
# ///
"""Full-page screenshot of a local HTML file at a given viewport width; prints {"page_errors": [...]} as JSON.
usage: uv run shot_html.py <file.html> <out.png> <width>"""
import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def launch(pw):
    try:
        return pw.chromium.launch()
    except Exception as e:  # noqa: BLE001
        if "Executable doesn't exist" not in str(e) and "playwright install" not in str(e):
            raise
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    return pw.chromium.launch()


html, out, width = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), int(sys.argv[3])
errors = []
with sync_playwright() as pw:
    b = launch(pw)
    page = b.new_page(viewport={"width": width, "height": 900})
    page.on("pageerror", lambda e: errors.append(str(e)[:200]))
    page.goto(html.as_uri(), wait_until="load")
    page.wait_for_timeout(500)
    out.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out), full_page=True)
    b.close()
print(json.dumps({"page_errors": errors}))
