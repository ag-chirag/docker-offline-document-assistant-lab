#!/usr/bin/env python3
"""Reject upload/prompt text and wrong-source UI elements as citation evidence."""

import json
import os
import sys

from playwright.sync_api import sync_playwright

from browser_rehearse import assistant_citation_state


CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    raise SystemExit("set CHROME_BIN to an installed Chrome/Chromium executable")

cases = [
    ("assistant citation", """
     <div class="chat-assistant"><div id="response-content-container">
     <div class="markdown-prose"><p>The time is 09:15.
     <button aria-label="View source: harbor-access.txt">harbor-access.txt</button></p></div>
     <button aria-label="View source: 1 harbor-access.txt">1 harbor-access.txt</button>
     </div></div>""", True),
    ("upload chip and prompt only", """
     <div class="chat-user">harbor-access.txt: what is the time?</div>
     <div class="chat-assistant"><div id="response-content-container">
     <div class="markdown-prose"><p>The time is 09:15.</p></div>
     </div></div>""", False),
    ("wrong assistant source", """
     <div class="chat-assistant"><div id="response-content-container">
     <div class="markdown-prose"><p>The time is 09:15.
     <button aria-label="View source: other.txt">other.txt</button></p></div>
     <button aria-label="View source: 1 other.txt">1 other.txt</button>
     </div></div>""", False),
]

results = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=CHROME, headless=True)
    page = browser.new_page()
    for name, html, expected_pass in cases:
        page.set_content(html)
        state = assistant_citation_state(page, "harbor-access.txt", "09:15")
        actual_pass = all(state[key] for key in (
            "assistant_answer_contains_expected", "assistant_citation_visible",
            "assistant_source_panel_visible",
        ))
        results.append({"control": name, "expected_pass": expected_pass,
                        "actual_pass": actual_pass, "control_pass": actual_pass == expected_pass})
    browser.close()
print(json.dumps(results, indent=2))
sys.exit(0 if all(result["control_pass"] for result in results) else 1)
