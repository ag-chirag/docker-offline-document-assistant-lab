#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
project="${LAB_PROJECT:-offline-doc-lab}"
base=(docker compose -p "$project" -f compose.yaml)
offline=(docker compose -p "$project" -f compose.yaml -f compose.offline.yaml)

wait_for_ui() {
  local port="${WEBUI_PORT:-$(sed -n 's/^WEBUI_PORT=//p' .env)}"
  port="${port:-3077}"
  local attempt
  for ((attempt = 1; attempt <= 60; attempt++)); do
    if curl --fail --silent --show-error --max-time 2 \
      "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "Local UI did not become ready at 127.0.0.1:${port} within 120 seconds." >&2
  return 1
}

if [[ ! -f .env ]]; then
  echo 'Create .env from .env.example and set unique secrets first.' >&2
  exit 2
fi
if grep -q 'replace-with-' .env; then
  echo 'Replace the placeholder secrets in .env before starting.' >&2
  exit 2
fi

case "${1:-}" in
  online)
    "${base[@]}" down --remove-orphans
    "${base[@]}" up -d --pull never
    wait_for_ui
    ;;
  prepare)
    case "${2:-all}" in
      generator) models=(qwen2.5:1.5b) ;;
      embedder) models=(all-minilm:latest) ;;
      all) models=(qwen2.5:1.5b all-minilm:latest) ;;
      *) echo 'prepare accepts generator, embedder, or all' >&2; exit 2 ;;
    esac
    for model in "${models[@]}"; do
      "${base[@]}" exec -T ollama ollama pull "$model"
    done
    "${base[@]}" exec -T ollama ollama list
    ;;
  offline)
    "${base[@]}" down --remove-orphans
    "${offline[@]}" up -d --pull never
    wait_for_ui
    ;;
  restart)
    "${offline[@]}" stop edge webui ollama
    "${offline[@]}" up -d --force-recreate --pull never
    wait_for_ui
    ;;
  inspect)
    "${offline[@]}" ps
    "${offline[@]}" exec -T webui sh -c 'ip route || cat /proc/net/route'
    "${offline[@]}" exec -T ollama sh -c 'ip route || cat /proc/net/route'
    docker network inspect "${project}_app" "${project}_access"
    ;;
  down)
    "${base[@]}" down --remove-orphans
    ;;
  destroy)
    "${base[@]}" down --remove-orphans --volumes
    ;;
  *)
    echo 'Usage: scripts/lab.sh {online|prepare [generator|embedder|all]|offline|restart|inspect|down|destroy}' >&2
    exit 2
    ;;
esac
