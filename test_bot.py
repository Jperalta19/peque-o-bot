import unittest
from unittest.mock import patch

import bot


class BotValidationTests(unittest.TestCase):
    def test_accepts_requested_platforms_and_rejects_other_hosts(self):
        self.assertTrue(bot.is_supported_url("https://www.instagram.com/reel/abc/"))
        self.assertTrue(bot.is_supported_url("https://www.facebook.com/reel/abc/"))
        self.assertTrue(bot.is_supported_url("https://x.com/user/status/123"))
        self.assertFalse(bot.is_supported_url("https://example.com/video"))

    def test_extracts_url_with_trailing_punctuation_removed(self):
        self.assertEqual(
            bot.extract_supported_url("Mira esto: https://x.com/user/status/123!"),
            "https://x.com/user/status/123",
        )

    def test_selects_combined_video_and_audio_when_ffmpeg_exists(self):
        info = {
            "duration": 30,
            "formats": [
                {"format_id": "v", "vcodec": "avc1", "acodec": "none", "tbr": 2000, "height": 720, "filesize": 10_000_000},
                {"format_id": "a", "vcodec": "none", "acodec": "mp4a", "abr": 128, "filesize": 500_000},
            ],
        }
        with patch("bot.shutil.which", return_value="/usr/bin/ffmpeg"):
            selected, height, _ = bot.select_format(info)
        self.assertEqual(selected, "v+a")
        self.assertEqual(height, 720)

    def test_all_videos_are_capped_at_720p(self):
        info = {
            "duration": 30,
            "formats": [
                {"format_id": "1080", "vcodec": "avc1", "acodec": "mp4a", "tbr": 4000, "height": 1080, "filesize": 15_000_000},
                {"format_id": "720", "vcodec": "avc1", "acodec": "mp4a", "tbr": 2500, "height": 720, "filesize": 9_000_000},
            ],
        }
        selected, height, _ = bot.select_format(info)
        self.assertEqual(selected, "720")
        self.assertEqual(height, 720)

    def test_rejects_formats_above_safe_download_limit(self):
        info = {
            "duration": 30,
            "formats": [
                {"format_id": "large", "vcodec": "avc1", "acodec": "mp4a", "height": 720, "filesize": 46 * 1024 * 1024},
                {"format_id": "small", "vcodec": "avc1", "acodec": "mp4a", "height": 480, "filesize": 20 * 1024 * 1024},
            ],
        }
        selected, height, size = bot.select_format(info)
        self.assertEqual(selected, "small")
        self.assertEqual(height, 480)
        self.assertLess(size, 49 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
