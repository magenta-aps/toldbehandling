# SPDX-FileCopyrightText: 2025 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0


class HistoryTimestampMixin:
    @property
    def sidste_ændringsdato(self) -> str | None:
        """Return ISO timestamp of latest historical record, or None if none exist."""
        latest = self.history.order_by("-history_date").first()  # type: ignore
        return latest.history_date.isoformat() if latest else None
