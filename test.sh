#!/bin/bash -eu

source ./.venv/Scripts/activate

(
    cd tests
    PYTHONPATH=.. pytest
)
