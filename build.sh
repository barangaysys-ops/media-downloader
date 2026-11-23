#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "--- Installing Python dependencies ---"
pip install --upgrade pip
pip install -r requirements.txt

echo "--- Installing Deno JS solver for YouTube extraction ---"
if ! command -v deno &> /dev/null; then
    curl -fsSL https://deno.land/install.sh | sh
    export DENO_INSTALL="$HOME/.deno"
    export PATH="$DENO_INSTALL/bin:$PATH"
fi

echo "--- Build completed successfully ---"
