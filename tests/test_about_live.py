from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "wiki" / "scripts"))

from model_registry import list_models  # noqa: E402


class AboutLiveContent(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.about = (REPO / "landing" / "index.html").read_text(
            encoding="utf-8"
        )

    def test_main_wiki_figures_come_from_live_manifest_counts(self) -> None:
        self.assertIn('const MAIN_WIKI_SLUG = "wiki";', self.about)
        self.assertIn('fetchJson("/wikis")', self.about)
        self.assertIn("Object.entries(wiki.counts || {})", self.about)
        self.assertIn('id="liveWikiStats"', self.about)
        self.assertNotIn('<div class="big">28</div>', self.about)
        self.assertNotIn("Built on a 28-source wiki", self.about)

    def test_model_catalogue_comes_from_registry(self) -> None:
        self.assertIn('fetchJson("/api/models")', self.about)
        self.assertIn('id="modelCatalogue"', self.about)
        self.assertIn("renderModels(models)", self.about)

    def test_about_explains_the_extensible_system(self) -> None:
        self.assertIn(
            "The Karpathy teach-back wiki is one shipped model, not the whole product.",
            self.about,
        )
        self.assertIn("Second Brain (PARA)", self.about)
        self.assertIn("SOPs-to-Skills", self.about)
        self.assertIn("New agent practices can be added as model manifests.", self.about)
        self.assertNotIn("A three-layer knowledge engine.", self.about)

    def test_all_current_shipped_models_are_discoverable(self) -> None:
        ids = {model.id for model in list_models()}
        self.assertTrue(
            {"karpathy-wiki", "second-brain", "sops-to-skills"}.issubset(ids)
        )

    def test_design_source_records_live_content_rule(self) -> None:
        design = (REPO / "wiki" / "training" / "design.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Product figures are observations, not marketing constants.", design)
        self.assertIn("The public model catalogue reads `/api/models`.", design)
        self.assertIn("Do not assume every base has `topics`", design)


if __name__ == "__main__":
    unittest.main()
