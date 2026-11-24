# Outage rehearsal report

All times below are UTC on 2026-11-23. The run used Docker Engine 29.2.1 in
Docker Desktop's Linux/ARM64 VM (kernel 6.12.69-linuxkit, 14 virtual CPUs,
8.2 GB VM RAM), Compose 5.0.2, Open WebUI v0.13.4, Ollama 0.40.17, and a
fresh Google Chrome 158.0.8127.37 context. The immutable image and model
identifiers are in [`../assets.lock.json`](../assets.lock.json), and the
sanitized runtime configuration is in [`effective-config.json`](effective-config.json).
The host remained connected; only the disposable browser profile and the
application/model network were subjected to the documented controls.

| Case | Observed result | Record |
| --- | --- | --- |
| Prepared warm offline | **Pass.** Upload and extraction completed; the retrieved passage named `harbor-access.txt` and contained `09:15`; the model answered `09:15` with citation `[1]`. Fresh Chrome loaded the UI (HTTP 200), displayed the source, and could not load external HTTPS. | [`cases/delivery-warm.json`](cases/delivery-warm.json), [`cases/delivery-browser-warm.json`](cases/delivery-browser-warm.json), [`ui-citation.png`](ui-citation.png) |
| Cold restart | **Pass.** All three container IDs changed while volumes were retained; the same document flow and a new browser context succeeded offline. | [`cases/delivery-cold-before.json`](cases/delivery-cold-before.json), [`cases/delivery-cold-after.json`](cases/delivery-cold-after.json), [`cases/delivery-cold.json`](cases/delivery-cold.json), [`cases/delivery-browser-cold.json`](cases/delivery-browser-cold.json), [`ui-cold.png`](ui-cold.png) |
| First ingestion after disconnection | **Pass.** The previously unseen `fresh-ingestion.txt` was parsed and indexed after the network cut. Its retrieved passage contained `marigold-jetty-906`; the answer reproduced that code with citation `[1]`. | [`cases/delivery-first-ingestion.json`](cases/delivery-first-ingestion.json) |
| Missing embedding asset | **Expected failure.** In a separate Compose project with only the generator pulled, upload processing returned `failed`. The WebUI log identified `Ollama embed error (404): model 'all-minilm:latest' not found`. The local UI remained accessible. | [`cases/delivery-missing-embedder.json`](cases/delivery-missing-embedder.json), [`missing-embedder-logs.txt`](missing-embedder-logs.txt), [`missing-embedder-status.png`](missing-embedder-status.png) |
| Re-prepared, then offline | **Pass.** After pulling the embedder during online preparation, asset verification matched both manifest hashes. Offline upload, extraction, retrieval and cited answer for `silver-bay-604` succeeded, as did a fresh browser run. | [`cases/delivery-restored-offline.json`](cases/delivery-restored-offline.json), [`cases/delivery-browser-restored.json`](cases/delivery-browser-restored.json), [`restored-status.png`](restored-status.png), [`ui-restored.png`](ui-restored.png) |

The `pass` fields in the JSON files are generated from actual HTTP/UI results,
retrieved passage contents, source filename, and answer text; they do not
infer answer quality from a successful API response alone. The browser reports
record the local HTTP status, source visibility, and the failed external
request separately. Each cited API and browser rehearsal returned exit status
0 for its expected outcome. The negative control's status is an expected
application failure, not a claim that ingestion succeeded.

The final review found a startup race: immediately after one cold Compose
restart, the edge proxy briefly returned HTTP 502 before WebUI was ready.
`scripts/lab.sh` now waits for the local `/health` endpoint after starting or
recreating containers. The current citation-aware repeat run, including a
newly created offline fixture and the negative-control recovery, is published
in [`final/README.md`](final/README.md). The table above remains the earlier
delivery's evidence and provenance.

The network observations are in [`network.json`](network.json): `webui` and
`ollama` were attached only to the internal `app` bridge, had no default
route, and could reach `ollama:11434` locally. Both returned DNS `SERVFAIL`
for `example.com` and `Network unreachable` for external HTTP to `1.1.1.1`.
The edge proxy was attached to both `app` and `access`, so it retained a route
through `access`. The browser used a dead per-process proxy with an explicit
loopback bypass; it did not test or disable all host traffic. These checks
demonstrate this bounded outage rehearsal, not a universal air gap or a
separate physical host deployment.

Reproduce the setup, warm/cold/first-ingestion and negative/recovery commands
from [`../README.md`](../README.md). The raw, sanitized container excerpts
are [`baseline-logs.txt`](baseline-logs.txt),
[`missing-embedder-logs.txt`](missing-embedder-logs.txt), and
[`restored-logs.txt`](restored-logs.txt). An initial exploratory 0.5B generator
produced an incorrect answer despite a correct retrieval, so the final
rehearsal uses the pinned 1.5B generator. Correct answers here are limited
to the three synthetic, short text fixtures and do not establish general
answer accuracy.
