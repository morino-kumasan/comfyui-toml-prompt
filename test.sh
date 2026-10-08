#!/bin/bash -eu

if [[ -d "./.venv" ]]; then
    source ./.venv/Scripts/activate
else
    python -m venv .venv
    source ./.venv/Scripts/activate
    python -m pip install -r ./tests/requirements.txt
fi

(
    cd tests
    PYTHONPATH=.. pytest
)
