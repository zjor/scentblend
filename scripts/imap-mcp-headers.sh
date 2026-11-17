#!/usr/bin/env bash
# Prints the imap-mcp request headers as JSON, for the Claude Code
# "headersHelper" setting. Values come from the environment or an env
# file, by default ./.env.local (override with IMAP_MCP_ENV_FILE). Needs jq.
#
# Required variables: IMAP_MCP_TOKEN, IMAP_USER, IMAP_PASSWORD.
# Optional: IMAP_HOST (only when the server allows more than one host).
set -euo pipefail

env_file="${IMAP_MCP_ENV_FILE:-./.env.local}"
IMAP_MCP_TOKEN="${IMAP_MCP_TOKEN:-}" IMAP_USER="${IMAP_USER:-}"
IMAP_PASSWORD="${IMAP_PASSWORD:-}" IMAP_HOST="${IMAP_HOST:-}"

# Read KEY=VALUE lines the same way the server reads .env.local: no shell
# expansion, an optional "export " prefix, optional matching quotes. The
# file is never executed. Only the variables below are taken from it, and
# a variable already set in the environment wins.
[[ -f "$env_file" ]] && while IFS= read -r line || [[ -n "$line" ]]; do
	line="${line#"${line%%[![:space:]]*}"}"
	line="${line%"${line##*[![:space:]]}"}"
	[[ -z "$line" || "$line" == \#* || "$line" != *=* ]] && continue
	line="${line#export }"
	key="${line%%=*}"
	key="${key%"${key##*[![:space:]]}"}"
	val="${line#*=}"
	val="${val#"${val%%[![:space:]]*}"}"
	if [[ ${#val} -ge 2 && ( "$val" == \"*\" || "$val" == \'*\' ) ]]; then
		val="${val:1:${#val}-2}"
	fi
	case "$key" in
	IMAP_MCP_TOKEN | IMAP_USER | IMAP_PASSWORD | IMAP_HOST)
		[[ -z "${!key}" ]] && printf -v "$key" '%s' "$val"
		;;
	esac
done <"$env_file"

for v in IMAP_MCP_TOKEN IMAP_USER IMAP_PASSWORD; do
	if [[ -z "${!v}" ]]; then
		echo "imap-mcp-headers: $v is not set (environment or $env_file)" >&2
		exit 1
	fi
done

# The values reach jq through its environment, not its arguments, so they
# never show in the process list. jq escapes them for JSON.
IMAP_MCP_H_AUTH="Bearer $IMAP_MCP_TOKEN" \
	IMAP_MCP_H_USER="$IMAP_USER" \
	IMAP_MCP_H_PASS="$IMAP_PASSWORD" \
	IMAP_MCP_H_HOST="$IMAP_HOST" \
	jq -n '{"Authorization": $ENV.IMAP_MCP_H_AUTH, "X-IMAP-Username": $ENV.IMAP_MCP_H_USER, "X-IMAP-Password": $ENV.IMAP_MCP_H_PASS}
	 + (if $ENV.IMAP_MCP_H_HOST != "" then {"X-IMAP-Host": $ENV.IMAP_MCP_H_HOST} else {} end)'
