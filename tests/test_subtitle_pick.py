"""Caption-track selection.

Regression cover for a silent data-loss bug: YouTube lists the live chat
replay of a stream or premiere inside the `subtitles` dict as `live_chat`,
offered only as ext "json". The picker's "any manual track" fallback selected
it, the fetcher could not parse "json", and because a track HAD been picked
the automatic captions were never consulted. Conference talks and premieres
came out with no transcript at all while YouTube had one all along.
"""
from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch

import _util  # noqa: F401  (path bootstrap)
import convert


def track(*exts: str) -> list[dict]:
    return [{"ext": e, "url": f"https://example.test/{e}"} for e in exts]


class FakeResponse:
    def __init__(self, body: str):
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


class PickSubtitle(unittest.TestCase):
    def test_live_chat_never_beats_real_auto_captions(self):
        subs = {"live_chat": track("json")}
        auto = {"en": track("json3", "vtt")}
        lang, source, formats = convert.pick_subtitle(subs, auto)
        self.assertEqual((lang, source), ("en", "auto"))
        self.assertTrue(formats)

    def test_live_chat_alone_yields_nothing(self):
        lang, source, formats = convert.pick_subtitle(
            {"live_chat": track("json")}, {})
        self.assertEqual((lang, source, formats), ("", "", []))

    def test_manual_english_still_wins(self):
        lang, source, _ = convert.pick_subtitle(
            {"en": track("vtt")}, {"en": track("vtt")})
        self.assertEqual((lang, source), ("en", "manual"))

    def test_unparseable_manual_track_falls_through_to_auto(self):
        # A manual track whose only format we cannot read must not be
        # treated as a successful pick.
        lang, source, _ = convert.pick_subtitle(
            {"de": track("json")}, {"en": track("vtt")})
        self.assertEqual((lang, source), ("en", "auto"))

    def test_non_english_is_better_than_nothing(self):
        lang, source, _ = convert.pick_subtitle({}, {"pt": track("vtt")})
        self.assertEqual((lang, source), ("pt", "auto"))

    def test_en_orig_is_accepted(self):
        lang, source, _ = convert.pick_subtitle({}, {"en-orig": track("srv3")})
        self.assertEqual((lang, source), ("en-orig", "auto"))

    def test_candidates_keep_manual_then_automatic_recovery_order(self):
        candidates = convert.subtitle_candidates(
            {"en": track("vtt"), "pt": track("vtt")},
            {"en": track("json3"), "fr": track("vtt")},
        )
        self.assertEqual(
            [(lang, source) for lang, source, _ in candidates],
            [("en", "manual"), ("pt", "manual"),
             ("en", "auto"), ("fr", "auto")],
        )

    @patch("convert.fetch_subtitle_text", side_effect=["", "auto recovered"])
    def test_failed_manual_fetch_falls_through_to_automatic(self, fetch):
        text, lang, source, count = convert.fetch_best_subtitle(
            {"en": track("vtt")}, {"en": track("json3")}
        )
        self.assertEqual((text, lang, source, count),
                         ("auto recovered", "en", "auto", 2))
        self.assertEqual(fetch.call_count, 2)


class UsableFormats(unittest.TestCase):
    def test_only_parseable_extensions_count(self):
        self.assertTrue(convert._usable(track("vtt")))
        self.assertTrue(convert._usable(track("json3")))
        self.assertTrue(convert._usable(track("srv3")))
        self.assertFalse(convert._usable(track("json")))
        self.assertFalse(convert._usable(track("ttml", "srv1")))
        self.assertFalse(convert._usable([]))
        self.assertFalse(convert._usable(None))


class FetchSubtitle(unittest.TestCase):
    def test_srv3_is_actually_parsed_as_xml(self):
        xml = (
            "<timedtext><body><p><s>Hello</s><s> world</s></p>"
            "<p>Second line</p></body></timedtext>"
        )
        self.assertEqual(convert.parse_srv3(xml), "Hello world Second line")

    @patch("convert.time.sleep")
    @patch(
        "convert.urllib.request.urlopen",
        side_effect=[
            OSError("temporary failure"),
            FakeResponse("WEBVTT\n\n00:00.000 --> 00:01.000\nRecovered text"),
        ],
    )
    def test_transient_fetch_gets_one_retry(self, urlopen, _sleep):
        text = convert.fetch_subtitle_text(track("vtt"))
        self.assertEqual(text, "Recovered text")
        self.assertEqual(urlopen.call_count, 2)

    @patch("convert.urllib.request.urlopen")
    def test_multiple_supported_urls_are_all_attempted(self, urlopen):
        urlopen.side_effect = [
            OSError("first URL failed"),
            OSError("first URL failed again"),
            FakeResponse("WEBVTT\n\n00:00.000 --> 00:01.000\nSecond URL"),
        ]
        formats = [
            {"ext": "vtt", "url": "https://example.test/first"},
            {"ext": "vtt", "url": "https://example.test/second"},
        ]
        with patch("convert.time.sleep"):
            self.assertEqual(
                convert.fetch_subtitle_text(formats), "Second URL"
            )
        self.assertEqual(urlopen.call_count, 3)


class ConvertFallbackOrder(unittest.TestCase):
    class FakeYDL:
        last_options = None

        def __init__(self, options):
            type(self).last_options = options

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, _url, download=False):
            assert download is False
            return {
                "id": "abcdefghijk",
                "title": "Recovery test",
                "webpage_url": "https://www.youtube.com/watch?v=abcdefghijk",
                "duration": 1200,
                "subtitles": {},
                "automatic_captions": {},
            }

    class ShortYDL(FakeYDL):
        def extract_info(self, url, download=False):
            info = super().extract_info(url, download=download)
            info["duration"] = 120
            return info

    @patch("convert.whisper_transcribe_via_groq")
    @patch("convert.whisper_transcribe_locally")
    @patch(
        "convert.fetch_best_subtitle",
        return_value=(("complete " * 180), "en", "manual", 1),
    )
    def test_complete_short_caption_does_not_trigger_audio(
        self, caption_fetch, local_whisper, groq_whisper
    ):
        fake_yt_dlp = types.SimpleNamespace(YoutubeDL=self.ShortYDL)
        with patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}):
            body, _title, _info = convert.convert_youtube(
                "https://www.youtube.com/watch?v=abcdefghijk"
            )
        caption_fetch.assert_called_once()
        local_whisper.assert_not_called()
        groq_whisper.assert_not_called()
        self.assertIn("## Transcript\n", body)

    @patch("convert.whisper_transcribe_via_groq",
           return_value=("audio " * 2000))
    @patch("convert.whisper_transcribe_locally", return_value=None)
    @patch(
        "convert.fetch_best_subtitle",
        return_value=(("partial " * 300), "en", "auto", 1),
    )
    def test_partial_captions_try_audio_before_guard(
        self, caption_fetch, local_whisper, groq_whisper
    ):
        fake_yt_dlp = types.SimpleNamespace(YoutubeDL=self.FakeYDL)
        with patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}):
            with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
                body, _title, _info = convert.convert_youtube(
                    "https://www.youtube.com/watch?v=abcdefghijk"
                )
        caption_fetch.assert_called_once()
        local_whisper.assert_called_once()
        groq_whisper.assert_called_once()
        self.assertEqual(
            self.FakeYDL.last_options["extractor_retries"], 3
        )
        self.assertIn("## Transcript (Whisper via Groq)", body)
        self.assertGreater(body.count("audio"), 1500)

    @patch("convert.whisper_transcribe_via_groq", return_value="")
    @patch("convert.whisper_transcribe_locally", return_value=None)
    @patch(
        "convert.fetch_best_subtitle",
        return_value=("", "", "", 0),
    )
    def test_no_captions_still_calls_audio_helper(
        self, caption_fetch, local_whisper, groq_whisper
    ):
        fake_yt_dlp = types.SimpleNamespace(YoutubeDL=self.FakeYDL)
        with patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}):
            with patch.dict(os.environ, {}, clear=True):
                body, _title, _info = convert.convert_youtube(
                    "https://www.youtube.com/watch?v=abcdefghijk"
                )
        caption_fetch.assert_called_once()
        local_whisper.assert_called_once()
        groq_whisper.assert_called_once()
        self.assertNotIn("## Transcript", body)

    @patch("convert.whisper_transcribe_via_groq")
    @patch(
        "convert.whisper_transcribe_locally",
        return_value=convert.local_whisper.LocalTranscript(
            text=("local words " * 900),
            language="en",
            model="tiny",
            engine="whisper.cpp",
            engine_version="1.9.1",
            segment_count=42,
        ),
    )
    @patch(
        "convert.fetch_best_subtitle",
        return_value=("", "", "", 0),
    )
    def test_complete_local_transcript_prevents_remote_fallback(
        self, caption_fetch, local_whisper, groq_whisper
    ):
        fake_yt_dlp = types.SimpleNamespace(YoutubeDL=self.FakeYDL)
        with patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}):
            with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
                body, _title, _info = convert.convert_youtube(
                    "https://www.youtube.com/watch?v=abcdefghijk"
                )
        caption_fetch.assert_called_once()
        local_whisper.assert_called_once()
        groq_whisper.assert_not_called()
        self.assertIn("## Transcript (local Whisper, en)", body)
        self.assertIn("whisper.cpp 1.9.1", body)
        self.assertIn("Audio stayed on this machine", body)


@unittest.skipUnless(
    os.environ.get("RIVERFED_RUN_LIVE_WHISPER") == "1",
    "set RIVERFED_RUN_LIVE_WHISPER=1 for the public-video integration check",
)
class LiveLocalWhisper(unittest.TestCase):
    def test_public_video_forced_through_local_path_passes_guard(self):
        url = "https://www.youtube.com/watch?v=Ib5GBkD555M"
        with patch(
            "convert.fetch_best_subtitle",
            return_value=("", "", "", 0),
        ):
            with patch("convert.whisper_transcribe_via_groq") as groq:
                body, title, _info = convert.convert_youtube(url)
        groq.assert_not_called()
        self.assertIn("## Transcript (local Whisper, en)", body)
        payload = convert.wrap_with_frontmatter(
            body,
            source=url,
            type_="youtube",
            title=title,
        )
        self.assertIsNone(convert._transcript.check(payload, "live-local.md"))
        self.assertGreater(
            convert._transcript.transcript_words(payload),
            3000,
        )


if __name__ == "__main__":
    unittest.main()
