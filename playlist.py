import datetime

import yt_dlp

from logs import logger

# Playlist metadata only. Everything that downloads lives in downloader.py.


class _ErrorCapturingLogger:
    """Forwards yt-dlp's output to the real logger, keeping the last error.

    ignoreerrors makes yt-dlp swallow the cause and simply return None, so the
    reason a playlist failed ("HTTP Error 403", "This playlist is private")
    only ever reaches us through this logger.
    """

    def __init__(self):
        self.last_error = None

    def debug(self, msg):
        logger.debug(msg)

    def info(self, msg):
        logger.info(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        self.last_error = str(msg).removeprefix("ERROR: ").strip()
        logger.error(msg)


def extract_playlist_info(url):
    """Return (playlist_title, [[url, title, duration], ...]).

    Raises RuntimeError carrying yt-dlp's own message when the playlist cannot
    be read, so the caller can show the user why rather than a generic failure.
    """
    capture = _ErrorCapturingLogger()
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        # Kept on so a playlist with a few unavailable videos still returns
        # the rest, rather than failing wholesale.
        "ignoreerrors": True,
        "logger": capture,
    }
    final_array = []
    playlist_title = "playlist"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # ignoreerrors returns None instead of raising. Reading .get() off that is
    # what used to surface as "'NoneType' object has no attribute 'get'",
    # hiding the real cause yt-dlp had already reported.
    if info is None:
        raise RuntimeError(capture.last_error or "YouTube returned no playlist data")

    playlist_title = info.get("title", playlist_title)
    for entry in info.get("entries", []):
        if not entry or "id" not in entry:
            continue
        duration = entry.get("duration") or 0
        final_array.append([
            f"https://www.youtube.com/watch?v={entry['id']}",
            entry.get("title", "Unknown"),
            str(datetime.timedelta(seconds=duration)),
        ])
    logger.info("Playlist entries fetched", extra={"count": len(final_array)})
    return playlist_title, final_array


def extract_video_info_from_array(final_array):
    """[[url, title, duration], ...] -> {title: url}"""
    return {row[1]: row[0] for row in final_array}


if __name__ == "__main__":
    import unittest.mock as _m

    class _FakeYDL:
        def __init__(self, result):
            self._result = result

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download=False):
            # Stand in for yt-dlp reporting the cause and then returning None,
            # which is exactly what ignoreerrors does on a hard failure.
            if self._result is None:
                _CAPTURE[0].error("ERROR: [youtube:tab] Unable to download API page: HTTP Error 403: Forbidden")
            return self._result

    _CAPTURE = [None]
    _orig = _ErrorCapturingLogger.__init__

    def _spy(self):
        _orig(self)
        _CAPTURE[0] = self

    with _m.patch.object(_ErrorCapturingLogger, "__init__", _spy):
        # A hard failure must reach the caller as yt-dlp's own words, not as an
        # AttributeError about NoneType.
        with _m.patch.object(yt_dlp, "YoutubeDL", lambda o: _FakeYDL(None)):
            try:
                extract_playlist_info("https://www.youtube.com/playlist?list=X")
            except RuntimeError as e:
                assert "403" in str(e), e
                assert "NoneType" not in str(e)
                assert not str(e).startswith("ERROR: "), e
            else:
                raise AssertionError("a None result must raise")

        # An empty-but-valid playlist is not an error.
        with _m.patch.object(yt_dlp, "YoutubeDL", lambda o: _FakeYDL({"title": "Empty", "entries": []})):
            assert extract_playlist_info("u") == ("Empty", [])

        # Unreadable entries are skipped without sinking the whole playlist.
        _entries = {"title": "Mix", "entries": [
            {"id": "aaa", "title": "One", "duration": 61},
            None,
            {"title": "no id"},
            {"id": "bbb", "title": "Two", "duration": None},
        ]}
        with _m.patch.object(yt_dlp, "YoutubeDL", lambda o: _FakeYDL(_entries)):
            title, rows = extract_playlist_info("u")
        assert title == "Mix"
        assert [r[1] for r in rows] == ["One", "Two"], rows
        assert rows[0][2] == "0:01:01" and rows[1][2] == "0:00:00", rows
        assert rows[0][0] == "https://www.youtube.com/watch?v=aaa"
        assert extract_video_info_from_array(rows) == {
            "One": "https://www.youtube.com/watch?v=aaa",
            "Two": "https://www.youtube.com/watch?v=bbb",
        }

    print("playlist self-checks ok")
