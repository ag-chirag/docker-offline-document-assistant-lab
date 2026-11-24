# Final revision validation

This directory contains the repeat run after citation validation was
strengthened. The first delivery's records remain in `../cases/`; they are
earlier evidence, not substituted for this run. The exact validated code,
Compose, lock and fixture file hashes are in [`revision.json`](revision.json).
It names the prior delivery commit as the baseline; the updated delivery
commit contains those file bytes and the evidence here.

The run used Docker Desktop's Linux/ARM64 Engine on an ARM64 Mac, Open WebUI
v0.13.4, Ollama 0.40.17 and preinstalled Chrome 158 in fresh contexts. See
[`../environment.json`](../environment.json) for kernel, CPU, memory and
Compose details. The host remained online. The application/model bridge was
internal, and only the disposable browser process used a dead HTTP proxy
with loopback bypass. The edge proxy retained a route through its separate
access bridge. This demonstrates the bounded workflow, not a physical air gap.

| Case | Result | Evidence |
| --- | --- | --- |
| Citation controls | **Pass:** the API validator accepted a supported citation and rejected a correct uncited answer, a wrong-source citation, a premature citation and an unrelated file. Browser DOM controls accepted an assistant citation and rejected upload/prompt-only text and a wrong assistant source. | [`citation-controls.json`](citation-controls.json) |
| Warm offline | **Pass:** upload, extraction, retrieved `harbor-access.txt` passage, correct `09:15` answer and source-mapped `[1]` citation. A fresh Chrome context showed the assistant citation and source row, loaded the local UI and could not load external HTTPS. | [`warm.json`](warm.json), [`browser-warm.json`](browser-warm.json), [`browser-warm.png`](browser-warm.png) |
| Cold restart | **Pass:** `ollama`, `webui` and `edge` acquired new container IDs while volumes were retained. The same API journey and another fresh browser context passed. | [`cold-before.json`](cold-before.json), [`cold-after.json`](cold-after.json), [`cold.json`](cold.json), [`browser-cold.json`](browser-cold.json), [`browser-cold.png`](browser-cold.png) |
| First ingestion after disconnection | **Pass:** the previously unindexed [`../../fixtures/revision-first.txt`](../../fixtures/revision-first.txt) was uploaded after the network cut. Its extracted and retrieved passage contained `indigo-wharf-573`; the answer reproduced that fact with a citation to this file's source. | [`first-ingestion.json`](first-ingestion.json) |
| Missing embedder and restoration | **Expected failure, then pass:** in a separate disposable volume, upload processing failed with the embedder removed; the WebUI log identified Ollama's missing-model 404. After online preparation and return to offline mode, the same file yielded a retrieved `silver-bay-604` passage, a correct cited answer and a fresh-browser citation. | [`missing-embedder.json`](missing-embedder.json), [`missing-embedder-log.txt`](missing-embedder-log.txt), [`restored.json`](restored.json), [`browser-restored.json`](browser-restored.json), [`browser-restored.png`](browser-restored.png) |

[`commands.json`](commands.json) records the exact command arguments,
environment overrides, UTC start/end times, exit status and bounded output
for every validation step. Its `CHROME_BIN` value is a portable placeholder
for the preinstalled Chrome 158 binary; no user-specific path is published.
Each API/browser case returned process exit 0 only after its own assertions
passed. For the missing-asset case, process exit 0 means the *expected*
application `status=failed` was observed. The restored asset check's exact
output, including all image/model digests, is in [`assets.txt`](assets.txt).

[`network.json`](network.json) records the final container IDs, pinned image
references and IDs, network attachments, internal bridge setting, routes and
local/external probes. `webui` and `ollama` had no default route, could reach
`ollama:11434` locally, and could not resolve `example.com` or connect to
external HTTP at `1.1.1.1`. The pinned Ollama image has no `nslookup`
executable: the first direct DNS probe exited 127. The successful repeat
used a disposable container from the already pinned nginx image with
`--network container:<ollama-id>` to probe the *same network namespace*.
That instrumentation failure and its corrected probe are both retained in
the command ledger.
[`negative-state.json`](negative-state.json) separately records the restored
negative-control project's container images and network attachments.

The API validator now requires the uploaded file ID and filename, the
supporting fact in its retrieved passage, the fact in the answer, and an
answer citation number that maps to that supporting source. The UI validator
checks the assistant's rendered citation button, its containing answer
paragraph and the opened source row. It cannot prove citation semantics for
arbitrary documents or general model accuracy; the checked passages and
facts are short synthetic fixtures. The browser proxy controls only that
fresh browser process, and the edge container is dual-homed.
