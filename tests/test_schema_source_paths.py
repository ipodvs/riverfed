"""Issue #5 — no shipped schema template documents the vault-escaping
`../../output/` source_file path."""
import re
import unittest

import _util


class SchemaSourcePaths(unittest.TestCase):
    def test_no_double_dot_output_in_source_file(self):
        offenders = []
        for schema in list((_util.PROJECT_DIR / "models").rglob("SCHEMA.md")) + \
                list((_util.PROJECT_DIR / "wikis").rglob("SCHEMA.md")):
            for i, line in enumerate(schema.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"source_file:\s*\.\./\.\./output/", line):
                    offenders.append(f"{schema}:{i}")
        self.assertEqual(offenders, [], f"vault-escaping source_file paths: {offenders}")


if __name__ == "__main__":
    unittest.main()
