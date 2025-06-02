#!/usr/bin/env bash
set -euo pipefail
# cd to src foler first
cd src
python -m spec_agent.api.server &
streamlit run spec_agent/ui/main.py --server.port 8000 --server.address 0.0.0.0
wait -n
