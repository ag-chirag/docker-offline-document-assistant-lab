#!/usr/bin/env python3
"""Focused controls for the citation check used by the end-to-end rehearsal."""

import json
import sys

from rehearse import assess_answer


def source(file_id, filename, passage):
    return {
        "source": {"type": "file", "id": file_id},
        "metadata": [{"file_id": file_id, "name": filename}],
        "document": [passage],
    }


support = source("uploaded-1", "harbor-access.txt", "The time is 09:15.")
distractor = source("other-2", "other.txt", "Another time is 10:00.")
controls = [
    ("supported citation", "The time is 09:15. [1]", [support], True),
    ("correct but uncited", "The time is 09:15.", [support], False),
    ("citation to wrong source", "The time is 09:15. [1]", [distractor, support], False),
    ("citation before fact", "[1] The time is 09:15.", [support], False),
    ("unrelated uploaded file", "The time is 09:15. [1]", [distractor], False),
]
results = []
for name, answer, sources, expected_pass in controls:
    assessment = assess_answer(
        answer, sources, expected="09:15", filename="harbor-access.txt",
        file_id="uploaded-1",
    )
    actual_pass = all((assessment["source_matches_uploaded_file"],
                       assessment["retrieved_fact"], assessment["answer_contains_fact"],
                       assessment["citation_matches_supporting_source"]))
    results.append({"control": name, "expected_pass": expected_pass,
                    "actual_pass": actual_pass, "control_pass": actual_pass == expected_pass})
print(json.dumps(results, indent=2))
sys.exit(0 if all(result["control_pass"] for result in results) else 1)
