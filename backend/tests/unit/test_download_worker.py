"""Unit tests for the media download and transcode worker."""
import os
import tempfile
import pytest

from app.workers.download_worker import _generate_fallback_media, _transcode_media


def test_generate_fallback_media_mp4():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "output.mp4")
        _generate_fallback_media(output_file, "mp4")

        assert os.path.isfile(output_file)
        assert os.path.getsize(output_file) > 0

        with open(output_file, "rb") as f:
            header = f.read(16)
            assert b"ftyp" in header


def test_generate_fallback_media_mp3():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "output.mp3")
        _generate_fallback_media(output_file, "mp3")

        assert os.path.isfile(output_file)
        assert os.path.getsize(output_file) > 0

        with open(output_file, "rb") as f:
            header = f.read(10)
            assert header.startswith(b"ID3")


def test_transcode_media_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "output.webm")
        _transcode_media("https://example.com/test", output_file, "webm", "720p")

        assert os.path.isfile(output_file)
        assert os.path.getsize(output_file) > 0
