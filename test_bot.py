import unittest
from unittest.mock import patch

import bot


class SelectFormatWithoutFfmpegTests(unittest.TestCase):
    def test_select_format_prefers_single_stream_when_ffmpeg_missing(self):
        info = {
            "duration": 30,
            "formats": [
                {
                    "format_id": "video-only",
                    "vcodec": "avc1",
                    "acodec": "none",
                    "tbr": 2500,
                    "height": 1080,
                    "filesize": 20_000_000,
                },
                {
                    "format_id": "audio-only",
                    "vcodec": "none",
                    "acodec": "mp4a",
                    "tbr": 128,
                    "filesize": 800_000,
                },
                {
                    "format_id": "combined",
                    "vcodec": "avc1",
                    "acodec": "mp4a",
                    "tbr": 2400,
                    "height": 1080,
                    "filesize": 18_000_000,
                },
            ],
        }

        with patch("bot.shutil.which", return_value=None):
            selected_format, _, _ = bot._select_format(info)

        self.assertEqual(selected_format, "video-only")

    def test_select_format_uses_merge_when_ffmpeg_is_available(self):
        info = {
            "duration": 30,
            "formats": [
                {
                    "format_id": "video-only",
                    "vcodec": "avc1",
                    "acodec": "none",
                    "tbr": 2500,
                    "height": 1080,
                    "filesize": 20_000_000,
                },
                {
                    "format_id": "audio-only",
                    "vcodec": "none",
                    "acodec": "mp4a",
                    "tbr": 128,
                    "filesize": 800_000,
                },
                {
                    "format_id": "combined",
                    "vcodec": "avc1",
                    "acodec": "mp4a",
                    "tbr": 2400,
                    "height": 1080,
                    "filesize": 18_000_000,
                },
            ],
        }

        with patch("bot.shutil.which", return_value="/usr/bin/ffmpeg"):
            selected_format, _, _ = bot._select_format(info)

        self.assertEqual(selected_format, "video-only+audio-only")


if __name__ == "__main__":
    unittest.main()
