#!/usr/bin/env bash
# source scripts/env.sh dev
#
# Dev routes to dev-home/. Prod is just `haxjobs` — uv tool already put it on your PATH.

case "${1:-}" in
    dev)
        cd "$(dirname "$(dirname "${BASH_SOURCE[0]}")")" || return 1
        source scripts/dev.sh 2>/dev/null
        echo "  state → $HAXJOBS_HOME"
        echo "  use   → uv run -- haxjobs ..."
        ;;
    *)
        echo "usage: source scripts/env.sh dev"
        echo ""
        echo "dev:  uv run + editable src, state in dev-home/"
        echo "prod: just type 'haxjobs' — uv tool already installed it globally"
        echo "      state lives at ~/.haxjobs/"
        ;;
esac
