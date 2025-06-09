#!/usr/bin/env bash
set -euo pipefail
# cd to src foler first
cd src
uvicorn spec.api.server:app --host 0.0.0.0 --port "${PORT:-9000}"