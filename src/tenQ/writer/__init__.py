# SPDX-FileCopyrightText: 2024 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

# Current versions of application code expects to import these classes
# from `tenQ.writer` (and not `tenQ.writer.tenq` or `tenQ.writer.g69`.)

from tenQ.writer.g69 import G69TransactionWriter  # noqa: F401
from tenQ.writer.tenq import TenQTransactionWriter  # noqa: F401
