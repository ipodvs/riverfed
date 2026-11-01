"""Every panel on the dashboard is scoped to ONE knowledge base.

Regression: creating a base switched `currentWiki` and re-fetched the staged
files and the pending count, but not the watched channels — so a brand-new
base showed the *previous* base's subscribed channels and capture log, as if
those channels fed it. Subscriptions are per-vault on disk
(`<vault>/.state/subscriptions.json`); only the UI was out of scope.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SCOPED_PANELS = ("refreshFiles()", "refreshPending()", "loadWatcher()")


def _between(src: str, start: str, end: str) -> str:
    i = src.index(start)
    return src[i:src.index(end, i)]


class VaultScopedPanels(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.src = (REPO / "index.html").read_text(encoding="utf-8")

    def test_vault_changed_refetches_every_scoped_panel(self) -> None:
        body = _between(self.src, "function vaultChanged() {", "\n    }")
        for call in SCOPED_PANELS:
            self.assertIn(call, body,
                          f"vaultChanged() must re-fetch {call}")

    def test_the_picker_rescopes_the_panels(self) -> None:
        handler = _between(self.src,
                           "vaultSelect.addEventListener('change'", "\n    });")
        self.assertIn("vaultChanged();", handler)

    def test_creating_a_base_rescopes_the_panels(self) -> None:
        # The bug: this handler called refreshFiles/refreshPending by hand and
        # forgot loadWatcher. Both switch paths now share one function.
        handler = _between(self.src, "currentWiki = json.wiki.slug;",
                           "} catch (e) {")
        self.assertIn("vaultChanged();", handler)
        for call in SCOPED_PANELS:
            self.assertNotIn(call, handler,
                             "create must go through vaultChanged(), not "
                             "re-list the scoped panels itself")

    def test_first_paint_loads_every_scoped_panel(self) -> None:
        boot = _between(self.src, "loadVaults().then(() => {", "\n    });")
        for call in SCOPED_PANELS:
            self.assertIn(call, boot)


if __name__ == "__main__":
    unittest.main()
