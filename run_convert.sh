#!/bin/bash

export LANG="en_US.utf8"
(cd /opt/c-calendar && /root/.local/bin/uv run ./convertcal.py)
