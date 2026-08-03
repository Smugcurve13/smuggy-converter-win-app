"""Offline check that MP4 quality selection picks the right stream.

Runs yt-dlp's real format selector against YouTube's actual 4K ladder, so it
catches selector regressions without a network call. Guards a bug where the
H.264 preference outranked resolution and a 4K request silently returned 810p.

Run: python tests/test_format_selection.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yt_dlp

from downloader import _format_opts

# A normal 16:9 ladder, where heights line up with YouTube's quality labels.
# Note there is no avc1 above 1080 - YouTube ships no H.264 beyond that.
FORMATS = [
    dict(format_id="18",  vcodec="avc1.42001E",   acodec="mp4a.40.2", height=360,  ext="mp4"),
    dict(format_id="135", vcodec="avc1.4d401e",   acodec="none",      height=480,  ext="mp4"),
    dict(format_id="136", vcodec="avc1.4d401f",   acodec="none",      height=720,  ext="mp4"),
    dict(format_id="137", vcodec="avc1.640028",   acodec="none",      height=1080, ext="mp4"),
    dict(format_id="248", vcodec="vp9",           acodec="none",      height=1080, ext="webm"),
    dict(format_id="399", vcodec="av01.0.08M.08", acodec="none",      height=1080, ext="mp4"),
    dict(format_id="271", vcodec="vp9",           acodec="none",      height=1440, ext="webm"),
    dict(format_id="400", vcodec="av01.0.12M.08", acodec="none",      height=1440, ext="mp4"),
    dict(format_id="313", vcodec="vp9",           acodec="none",      height=2160, ext="webm"),
    dict(format_id="401", vcodec="av01.0.12M.08", acodec="none",      height=2160, ext="mp4"),
    dict(format_id="140", vcodec="none", acodec="mp4a.40.2", height=None, ext="m4a"),
    dict(format_id="251", vcodec="none", acodec="opus",      height=None, ext="webm"),
]
for _f in FORMATS:
    _f.update(url="u", protocol="https", tbr=100, filesize=None)


def pick(height):
    """(video_codec, video_height, audio_codec) our options select at this cap.

    Sorting is applied by yt-dlp's sorter, not by the format selector, so the
    formats must be sorted first exactly as a real run would - otherwise the sort
    silently has no effect and the test passes on the wrong reasons.
    """
    opts = _format_opts("mp4", height)
    ydl = yt_dlp.YoutubeDL({"quiet": True, "simulate": True, "format": opts["format"]})
    info = {"formats": [dict(f) for f in FORMATS], "incomplete_formats": False}
    ydl.sort_formats(info)
    chosen = next(iter(ydl.build_format_selector(opts["format"])(info)))
    parts = chosen.get("requested_formats") or [chosen]
    video = next((p for p in parts if p["vcodec"] != "none"), None)
    audio = next((p for p in parts if p["acodec"] != "none"), None)
    return (video["vcodec"].split(".")[0], video["height"],
            audio["acodec"].split(".")[0] if audio else None)


def main():
    for cap in (2160, 1440, 1080, 720, 480):
        vcodec, height, acodec = pick(cap)
        print(f"{cap:>5}p -> {vcodec:<5} {height}p  audio={acodec}")
        assert height <= cap, f"{cap}: height {height} exceeds the cap"

    # H.264 must still win where it exists, so ordinary downloads stay playable.
    assert pick(1080)[0] == "avc1", "H.264 must win at <=1080p"
    assert pick(720)[0] == "avc1", "H.264 must win at 720p"
    assert pick(1080)[2] == "mp4a", "AAC must pair with H.264"

    # Above 1080p only AV1/VP9 exist; AV1 is the one that belongs in an MP4.
    assert pick(2160)[0] == "av01", "4K must be AV1, not VP9 or a downgraded H.264"
    assert pick(1440)[0] == "av01", "1440p must be AV1"

    # The regression this file exists for: 4K must actually be 4K. Before the
    # fix this returned 1080 - an unconditional H.264 tier outranked height.
    assert pick(2160)[1] == 2160, f"4K returned {pick(2160)[1]}p - resolution lost to codec"
    assert pick(1440)[1] == 1440, f"1440p returned {pick(1440)[1]}p"

    # Opus in an MP4 has the same playback problem AV1 does; AAC must be chosen
    # wherever an AAC track exists.
    for cap in (2160, 1440, 1080, 720, 480):
        assert pick(cap)[2] == "mp4a", f"{cap}p got {pick(cap)[2]} audio, expected mp4a"

    print("\nPASS: resolution wins first, H.264 at <=1080p, AV1 above, cap respected")


if __name__ == "__main__":
    main()
