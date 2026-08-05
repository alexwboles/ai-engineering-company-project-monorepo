#!/bin/sh
set -eu

cleanup() {
  kill 0
}

trap cleanup INT TERM EXIT

npm --prefix website run dev -- --hostname 0.0.0.0 --port 3000 &
website_pid="$!"

npm --prefix backoffice run dev -- --hostname 0.0.0.0 --port 3001 &
backoffice_pid="$!"

wait "$website_pid" "$backoffice_pid"
