<!---
SPDX-FileCopyrightText: 2024 Magenta ApS <info@magenta.dk>

SPDX-License-Identifier: MPL-2.0
-->

# 10Q

Basic API for writing 10Q files

# Running the unittest suite

Running `docker compose run test` should execute the unittests and display test coverage.

Coverage results are saved in `./coverage-results/`, which may be imported into your IDE, if it supports displaying
code coverage inline in source files. In PyCharm, run `Show Coverage Data`, and select both generated files in the
folder (`coverage.coverage` *and* `coverage.xml`.)
