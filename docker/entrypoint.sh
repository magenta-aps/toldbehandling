#!/bin/bash

# SPDX-FileCopyrightText: 2024 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

set -eu

TEST=${TEST:=true}

if [ "${TEST,,}" = true ]; then
  coverage run -m unittest
  coverage combine
  coverage report --skip-empty --show-missing
  coverage xml -o /coverage-results/coverage.xml
fi

exec "$@"
