#!/bin/bash

export LANG="en_US.utf8"
(cd /opt/c-calendar && uv run ./convertcal.py)
