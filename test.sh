#!/bin/bash -eu

(
    cd tests
    PYTHONPATH=.. pytest
)
