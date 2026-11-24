#!/bin/sh
# Prints the YouTrack MCP request headers as JSON, for the Claude Code
# "headersHelper" setting. Reads YOUTRACK_API_TOKEN from the environment or
# from .env.local in the project root. The env file is parsed, never sourced,
# so values with shell-special characters (e.g. passwords) do not break it.
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(dirname "$script_dir")

YOUTRACK_ENV_FILE="$project_dir/.env.local" exec python3 -I -c '
import json
import os
import sys

token = os.environ.get("YOUTRACK_API_TOKEN", "")
path = os.environ["YOUTRACK_ENV_FILE"]
if not token and os.path.isfile(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            key, val = line.split("=", 1)
            if key.strip() != "YOUTRACK_API_TOKEN":
                continue
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"\x27":
                val = val[1:-1]
            token = val

if not token:
    sys.exit("youtrack-headers: YOUTRACK_API_TOKEN is not set (environment or .env.local)")

print(json.dumps({"Authorization": "Bearer " + token}))
'
