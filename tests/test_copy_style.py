from __future__ import annotations

import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
COPY_FILES = (
    REPO / "index.html",
    *sorted((REPO / "landing").rglob("*.html")),
    *sorted((REPO / "landing").rglob("*.js")),
    *sorted((REPO / "landing").rglob("*.md")),
    REPO / "wiki" / "training" / "design.md",
    *sorted((REPO / "designs").rglob("*.md")),
)


class CopyStyle(unittest.TestCase):
    def test_user_facing_copy_has_no_em_dash(self) -> None:
        offenders: list[str] = []
        for path in COPY_FILES:
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if "\N{EM DASH}" in line or "&mdash;" in line.lower():
                    offenders.append(f"{path.relative_to(REPO)}:{line_number}")

        self.assertEqual(
            offenders,
            [],
            "Em dashes are not part of Riverfed copy style: "
            + ", ".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
