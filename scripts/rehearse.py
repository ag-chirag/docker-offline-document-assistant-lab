#!/usr/bin/env python3
"""Run one real upload → processing → retrieval → answer journey via Open WebUI."""

import argparse
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def local_env():
    values = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    return values


def call(base, path, *, token=None, payload=None, content_type="application/json", timeout=120):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = content_type
    request = Request(base + path, data=payload, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:1000]
        return exc.code, {"error": body}


def upload_body(path):
    boundary = "codex-" + secrets.token_hex(12)
    data = path.read_bytes()
    name = path.name.replace('"', "")
    kind = mimetypes.guess_type(name)[0] or "text/plain"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
        f"Content-Type: {kind}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def assess_answer(message, sources, *, expected, filename, file_id):
    """Check the answer and its 1-based citations against the uploaded source.

    The pinned Open WebUI response numbers the `sources` array from 1 in its
    answer text. A filename elsewhere in the response is insufficient.
    """
    matching_indices = []
    supporting_indices = []
    for index, source in enumerate(sources, 1):
        identity = source.get("source") or {}
        metadata = source.get("metadata") or []
        if identity.get("type") != "file" or identity.get("id") != file_id:
            continue
        if not any(meta.get("file_id") == file_id and meta.get("name") == filename
                   for meta in metadata):
            continue
        matching_indices.append(index)
        if any(expected in passage for passage in source.get("document") or []):
            supporting_indices.append(index)

    fact_position = message.find(expected)
    answer_has_fact = fact_position >= 0
    citations = [int(match.group(1)) for match in re.finditer(r"\[(\d+)\]", message)
                 if answer_has_fact and fact_position + len(expected) <= match.start()
                 <= fact_position + len(expected) + 160]
    return {
        "source_matches_uploaded_file": bool(matching_indices),
        "retrieved_fact": bool(supporting_indices),
        "answer_contains_fact": answer_has_fact,
        "answer_citations_after_fact": citations,
        "citation_matches_supporting_source": bool(set(citations) & set(supporting_indices)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("document", type=Path)
    parser.add_argument("question")
    parser.add_argument("--expected", required=True, help="distinct fact expected in retrieved text and answer")
    parser.add_argument("--expect-processing-failure", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    env = local_env()
    base = "http://127.0.0.1:" + os.environ.get("WEBUI_PORT", env.get("WEBUI_PORT", "3077"))
    record = {"case": args.case, "started_at": now(), "document": args.document.name,
              "question": args.question, "expected": args.expected, "steps": []}

    def step(name, status, data):
        record["steps"].append({"at": now(), "name": name, "http_status": status, "data": data})

    try:
        status, result = call(base, "/api/v1/auths/signin", payload=json.dumps({
            "email": env["WEBUI_ADMIN_EMAIL"], "password": env["WEBUI_ADMIN_PASSWORD"]
        }).encode())
        token = result.pop("token", None)
        result.pop("profile_image_url", None)
        step("local_signin", status, {"role": result.get("role"), "token_received": bool(token)})
        if status != 200 or not token:
            raise RuntimeError("local sign-in failed")

        body, kind = upload_body(args.document)
        status, result = call(base, "/api/v1/files/", token=token, payload=body,
                              content_type=kind, timeout=120)
        file_id = result.get("id")
        step("upload", status, {"file_id": file_id, "error": result.get("error")})
        if status != 200 or not file_id:
            raise RuntimeError("file upload failed")

        deadline = time.monotonic() + 180
        while True:
            status, processing = call(base, f"/api/v1/files/{file_id}/process/status", token=token)
            if status != 200:
                raise RuntimeError(f"processing status returned HTTP {status}")
            if processing.get("status") in ("completed", "failed"):
                break
            if time.monotonic() > deadline:
                raise TimeoutError("file processing exceeded 180 seconds")
            time.sleep(2)
        step("processing", status, processing)
        if args.expect_processing_failure:
            record["pass"] = processing.get("status") == "failed"
            return 0 if record["pass"] else 1
        if processing.get("status") != "completed":
            raise RuntimeError("file processing failed")

        status, content = call(base, f"/api/v1/files/{file_id}/data/content", token=token)
        step("extracted_text", status, content)
        if status != 200 or args.expected not in json.dumps(content):
            raise RuntimeError("extracted document lacks expected fact")

        payload = {
            "model": "qwen2.5:1.5b", "stream": False,
            "messages": [{"role": "user", "content": args.question + " Cite the attached file."}],
            "files": [{"type": "file", "id": file_id}],
            "params": {"function_calling": "legacy"},
        }
        status, answer = call(base, "/api/chat/completions", token=token,
                              payload=json.dumps(payload).encode(), timeout=180)
        message = (answer.get("choices") or [{}])[0].get("message", {}).get("content", "")
        sources = answer.get("sources", [])
        step("chat", status, {"answer": message, "sources": sources, "error": answer.get("error")})
        record["assessment"] = assess_answer(
            message, sources, expected=args.expected,
            filename=args.document.name, file_id=file_id,
        )
        record["pass"] = status == 200 and all((
            record["assessment"]["source_matches_uploaded_file"],
            record["assessment"]["retrieved_fact"],
            record["assessment"]["answer_contains_fact"],
            record["assessment"]["citation_matches_supporting_source"],
        ))
        return 0 if record["pass"] else 1
    except (OSError, URLError, RuntimeError, TimeoutError, KeyError) as exc:
        record["error"] = str(exc)
        record["pass"] = False
        return 1
    finally:
        record["finished_at"] = now()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"case": args.case, "pass": record["pass"],
                          "assessment": record.get("assessment"), "error": record.get("error"),
                          "record": str(args.output)}))


if __name__ == "__main__":
    sys.exit(main())
