#!/usr/bin/env python3
"""Exercise the offline UI in a fresh Chrome profile with browser-only egress blocked.

Install Playwright in an isolated virtual environment and set CHROME_BIN to an
existing Chrome/Chromium executable. No browser download is performed here.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("question")
    parser.add_argument("--screenshot", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    env = dict(line.split("=", 1) for line in (ROOT / ".env").read_text().splitlines()
               if line and not line.startswith("#"))
    port = os.environ.get("WEBUI_PORT", env.get("WEBUI_PORT", "3077"))
    base = f"http://127.0.0.1:{port}"
    chrome = os.environ.get("CHROME_BIN")
    if not chrome:
        parser.error("set CHROME_BIN to an installed Chrome/Chromium executable")
    report = {"started_at": datetime.now(timezone.utc).isoformat(),
              "browser": chrome, "local_url": base, "document": args.document.name,
              "question": args.question, "fresh_context": True,
              "browser_egress_control": "dead 127.0.0.1:9 HTTP proxy; explicit loopback bypass"}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=chrome, headless=True,
                args=["--proxy-server=http://127.0.0.1:9",
                      "--proxy-bypass-list=127.0.0.1;localhost"],
            )
            context = browser.new_context()
            page = context.new_page()
            response = page.goto(base, wait_until="domcontentloaded", timeout=30000)
            report["local_http_status"] = response.status if response else None
            page.get_by_placeholder("Enter Your Email").fill(env["WEBUI_ADMIN_EMAIL"])
            page.get_by_placeholder("Enter Your Password").fill(env["WEBUI_ADMIN_PASSWORD"])
            page.get_by_role("button", name="Sign in").click()
            page.get_by_role("button", name="User menu").wait_for(timeout=20000)
            page.wait_for_timeout(1000)
            release_note = page.get_by_text("Okay, Let's Go!")
            if release_note.is_visible():
                release_note.click()
            selected = page.get_by_role("button", name=re.compile("Selected model:"))
            if "qwen2.5:1.5b" not in (selected.get_attribute("aria-label") or ""):
                selected.click()
                page.get_by_text("qwen2.5:1.5b", exact=True).last.click()
            page.locator('input[type="file"]').first.set_input_files(str(args.document.resolve()))
            page.get_by_role("textbox", name=re.compile("How can I help|Send a Message")).fill(args.question)
            page.get_by_role("textbox", name=re.compile("How can I help|Send a Message")).press("Enter")
            source_button = page.get_by_role("button", name=re.compile(r"Toggle [1-9][0-9]* source"))
            source_button.wait_for(timeout=120000)
            page.wait_for_timeout(3000)
            source_button.click()
            report["ui_text"] = page.locator("body").inner_text()[-3000:]
            report["source_visible"] = args.document.name in report["ui_text"]
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(args.screenshot), full_page=True)
            try:
                page.goto("https://example.com/", timeout=15000)
                report["external_http_blocked"] = False
            except Exception as exc:
                report["external_http_blocked"] = True
                report["external_error"] = str(exc).splitlines()[0]
            report["passed_browser_controls"] = (
                report["local_http_status"] == 200 and report["source_visible"]
                and report["external_http_blocked"]
            )
            browser.close()
    except Exception as exc:
        report["error"] = str(exc).splitlines()[0]
        report["passed_browser_controls"] = False
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report.get(key) for key in
                      ("passed_browser_controls", "local_http_status", "source_visible",
                       "external_http_blocked", "error")}))
    return 0 if report["passed_browser_controls"] else 1


if __name__ == "__main__":
    sys.exit(main())
