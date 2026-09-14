#!/usr/bin/env bash
set -euo pipefail
git submodule update --remote tradingagents-core
python -m pip install -e ./tradingagents-core
git -C tradingagents-core rev-parse HEAD
