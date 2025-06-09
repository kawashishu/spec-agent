#!/usr/bin/env bash
set -euo pipefail
# cd to src foler first
cd src
streamlit run spec/ui/app.py
wait -n
