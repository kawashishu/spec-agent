#!/usr/bin/env bash
set -euo pipefail
# cd to src foler first
cd src
python api.py &
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0
wait -n
