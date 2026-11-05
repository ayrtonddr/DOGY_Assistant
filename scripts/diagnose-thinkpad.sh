#!/usr/bin/env bash
set -euo pipefail
printf '=== OS ===\n'; cat /etc/os-release | head -6
printf '\n=== CPU ===\n'; lscpu | grep -E 'Architecture:|Model name:|CPU\(s\):' || true
printf '\n=== RAM ===\n'; free -h
printf '\n=== Storage ===\n'; df -h .
printf '\n=== Audio ===\n'; command -v pactl >/dev/null && pactl info | head -12 || true
printf '\n=== GPU ===\n'; command -v lspci >/dev/null && lspci | grep -Ei 'vga|3d|display' || true
printf '\n=== Python ===\n'; python3 --version
