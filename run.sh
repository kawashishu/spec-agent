#!/usr/bin/env bash
set -euo pipefail
# cd to src foler first
cd src
# Start the FastAPI backend on port 9000
python -m spec.api.server &
streamlit run spec.ui.app --server.port 8000 --server.address 0.0.0.0
wait -n
