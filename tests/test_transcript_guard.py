"""The transcript guard: is a converted file usable as a source?

Everything downstream rests on the transcript, so both convert.py and
ingest.py check the same rule. These tests cover the shapes that actually
occurred: a caption-less video that looked like a valid file, and a real
transcript whose heading carries a suffix.
"""
from __future__ import annotations

import unittest

import _util  # noqa: F401  (path bootstrap)
import _transcript


def video(
    transcript: str | None,
    words: int = 0,
    duration: str | None = None,
) -> str:
    head = '---\nsource: "https://youtube.com/watch?v=x"\ntype: "youtube"\n'
    head += 'title: "A talk"\n---\n\n# A talk\n\n## Metadata\n\n- x\n\n## Description\n\nblurb\n'
    if duration:
        head = head.replace("- x", f"- **Duration:** {duration}")
    if transcript is not None:
        head += f"\n## {transcript}\n\n" + ("word " * words)
    return head


class VideoDetection(unittest.TestCase):
    def test_youtube_requires_a_transcript(self):
        self.assertTrue(_transcript.is_video(video("Transcript", 2000)))

    def test_web_article_is_exempt(self):
        article = '---\ntype: "url"\nsource: "https://example.com/post"\n---\n\n# Post\n\nbody'
        self.assertFalse(_transcript.is_video(article))
        self.assertIsNone(_transcript.check(article))

    def test_dropped_file_is_exempt(self):
        f = '---\ntype: "text"\nsource: "notes.md"\n---\n\n# Notes\n\nbody'
        self.assertIsNone(_transcript.check(f))


class HeadingMatching(unittest.TestCase):
    def test_heading_with_caption_source_suffix_counts(self):
        # Real conversions write "## Transcript (auto-generated, en)". An
        # earlier guard anchored the heading with `$` and so rejected every
        # genuine transcript in the vault.
        md = video("Transcript (auto-generated, en)", 2000)
        self.assertGreater(_transcript.transcript_words(md), 1500)
        self.assertIsNone(_transcript.check(md))

    def test_plain_heading_counts(self):
        self.assertIsNone(_transcript.check(video("Transcript", 2000)))

    def test_section_after_transcript_is_not_counted(self):
        md = video("Transcript", 1500) + "\n## Visual content\n\n" + ("x " * 5000)
        self.assertLess(_transcript.transcript_words(md), 2000)

    def test_local_timestamps_do_not_inflate_word_count(self):
        timestamped = "\n".join(
            f"[00:00:{i:02d}.000 - 00:00:{i:02d}.500] spoken word"
            for i in range(20)
        )
        md = (
            '---\ntype: "youtube"\n---\n\n'
            "## Transcript (local Whisper, en)\n\n"
            + timestamped
        )
        self.assertEqual(_transcript.transcript_words(md), 40)

    def test_duration_parses_minutes_and_hours(self):
        self.assertEqual(
            _transcript.duration_seconds(video("Transcript", 100, "2:05")),
            125,
        )
        self.assertEqual(
            _transcript.duration_seconds(video("Transcript", 100, "1:02:03")),
            3723,
        )


class Rejections(unittest.TestCase):
    def test_missing_transcript_is_rejected(self):
        problem = _transcript.check(video(None), "talk.md")
        self.assertIsNotNone(problem)
        self.assertIn("no '## Transcript' section", problem)
        self.assertIn("talk.md", problem)

    def test_message_does_not_blame_youtube_outright(self):
        # The old convert.py message said captions "may be disabled", which
        # sent people looking at YouTube when the bug was ours.
        problem = _transcript.check(video(None), "talk.md")
        self.assertIn("Re-run convert.py", problem)

    def test_fragment_is_rejected(self):
        problem = _transcript.check(video("Transcript", 300), "talk.md")
        self.assertIsNotNone(problem)
        self.assertIn("300 words", problem)

    def test_full_transcript_passes(self):
        self.assertIsNone(_transcript.check(video("Transcript", 5000)))

    def test_complete_short_video_is_not_rejected_by_long_form_floor(self):
        md = video("Transcript", 180, "2:00")
        self.assertEqual(_transcript.minimum_words(120), 90)
        self.assertIsNone(_transcript.check(md))

    def test_partial_long_video_still_fails_duration_aware_floor(self):
        md = video("Transcript (auto-generated, en)", 300, "20:00")
        diagnosis = _transcript.diagnose(md, "talk.md")
        self.assertEqual(diagnosis["status"], "blocked")
        self.assertEqual(diagnosis["code"], "incomplete_transcript")
        self.assertEqual(diagnosis["minimum_words"], 900)
        self.assertEqual(diagnosis["provenance"], "automatic captions")
        self.assertEqual(diagnosis["language"], "en")
        self.assertIn("at least 900", diagnosis["problem"])

    def test_missing_transcript_has_actionable_failure_code(self):
        diagnosis = _transcript.diagnose(video(None, duration="10:00"))
        self.assertEqual(diagnosis["status"], "blocked")
        self.assertEqual(diagnosis["code"], "missing_transcript")
        self.assertIn("local Whisper", diagnosis["problem"])


if __name__ == "__main__":
    unittest.main()
