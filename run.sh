#!/usr/bin/env bash
set -euo pipefail
# cd to src foler first
cd src
chainlit run spec/ui/cl_app.py -w
wait -n
