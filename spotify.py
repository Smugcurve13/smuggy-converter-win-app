"""Spotify playlist downloads via an Exportify CSV.

Spotify has no public audio API, so the track list comes from a CSV exported at
https://exportify.net and each track is matched on YouTube. Spotify's metadata is
then written to the file, which is the whole point - YouTube titles like
"Song (Official Video)", its description and its lyrics make for terrible tags.
"""

import csv
import json
import os
import urllib.parse
import urllib.request

from mutagen.id3 import APIC, ID3, TALB, TCON, TDRC, TIT2, TPE1, TPE2, TPOS, TRCK
from mutagen.mp3 import MP3

from downloader import download_and_convert
from file_utils import MEDIA_DIR, sanitize_filename
from logs import logger

# Exportify's column names have changed across versions and forks, so match on
# the first header that is actually present rather than one fixed spelling.
_COLUMNS = {
    "track": ["Track Name", "Track"],
    "artists": ["Artist Name(s)", "Artist Name", "Artists", "Artist"],
    "album": ["Album Name", "Album"],
    "album_artists": ["Album Artist Name(s)", "Album Artist Name", "Album Artist"],
    "release_date": ["Album Release Date", "Release Date"],
    "image_url": ["Album Image URL", "Album Image", "Image URL"],
    "disc": ["Disc Number", "Disc"],
    "track_no": ["Track Number", "Track #"],
    "genre": ["Genres", "Genre"],
    "uri": ["Track URI", "Spotify URI", "URI"],
}


def _pick(row, names):
    """First present, non-empty value among the candidate column names."""
    for name in names:
        value = (row.get(name) or "").strip()
        if value:
            return value
    return ""


def read_exportify_csv(path):
    """Parse an Exportify CSV into a list of track dicts. Rows without a name are skipped."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")

    tracks = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            track = {key: _pick(row, names) for key, names in _COLUMNS.items()}
            if not track["track"]:
                continue
            tracks.append(track)
        headers = reader.fieldnames or []

    if not tracks:
        raise ValueError(
            "No tracks found. Is this an Exportify CSV? Expected a 'Track Name' column."
        )

    missing = [k for k in ("album", "release_date", "image_url") if not any(t[k] for t in tracks)]
    logger.info(
        "Exportify CSV parsed",
        extra={"path": path, "tracks": len(tracks), "headers": len(headers), "absent": missing},
    )
    return tracks


def _cover_url_from_uri(uri):
    """Album art URL from a spotify:track: URI via the public oEmbed endpoint.

    Older Exportify exports carry no image column at all. oEmbed needs no API key
    or login, so it fills that gap without adding an auth story.
    """
    if not uri or "track" not in uri:
        return ""
    track_id = uri.rstrip("/").split(":")[-1].split("/")[-1].split("?")[0]
    endpoint = "https://open.spotify.com/oembed?url=" + urllib.parse.quote(
        f"https://open.spotify.com/track/{track_id}", safe=""
    )
    try:
        with urllib.request.urlopen(endpoint, timeout=15) as resp:
            return json.load(resp).get("thumbnail_url") or ""
    except Exception as e:
        logger.warning("Spotify oEmbed lookup failed", extra={"uri": uri, "error": str(e)})
        return ""


def _fetch_cover(url):
    """Album art bytes, or None. ponytail: stdlib urllib, not a requests dependency."""
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        logger.warning("Cover art fetch failed", extra={"url": url, "error": str(e)})
        return None


def _embed_metadata(mp3_path, track, cover):
    """Write Spotify's metadata onto the file.

    The download runs with source_metadata=False, so nothing from YouTube is
    present. Tags are cleared outright rather than frame-by-frame so no future
    field can survive into the result.
    """
    audio = MP3(mp3_path, ID3=ID3)
    audio.delete()
    audio.tags = ID3()
    tags = audio.tags

    tags.add(TIT2(encoding=3, text=track["track"]))
    for frame, key in (
        (TPE1, "artists"), (TALB, "album"), (TPE2, "album_artists"),
        (TDRC, "release_date"), (TRCK, "track_no"), (TPOS, "disc"), (TCON, "genre"),
    ):
        if track.get(key):
            tags.add(frame(encoding=3, text=track[key]))
    if cover:
        tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover))

    audio.save()


def download_spotify_csv(csv_path, quality, target_dir=None, progress_callback=None):
    """Download every track in an Exportify CSV. Returns (downloaded, [failed track names])."""
    tracks = read_exportify_csv(csv_path)
    base_dir = target_dir if target_dir else MEDIA_DIR
    playlist_dir = os.path.join(
        base_dir, sanitize_filename(os.path.splitext(os.path.basename(csv_path))[0]) or "spotify"
    )
    os.makedirs(playlist_dir, exist_ok=True)

    done, failed, no_art = [], [], 0
    total = len(tracks)
    for idx, track in enumerate(tracks):
        name = f"{track['track']} - {track['artists']}" if track["artists"] else track["track"]
        try:
            # ytsearch1 picks the top match; "<title> <artist>" ranks the real
            # track above covers and lyric videos.
            query = f"{track['track']} {track['artists']}".strip()
            filename = download_and_convert(
                f"ytsearch1:{query}",
                "mp3",
                quality,
                target_dir=playlist_dir,
                title=name,
                source_metadata=False,
                throttle=True,
            )
            cover = _fetch_cover(track["image_url"] or _cover_url_from_uri(track["uri"]))
            if not cover:
                no_art += 1
            _embed_metadata(os.path.join(playlist_dir, filename), track, cover)
            done.append(filename)
        except Exception as e:
            logger.error("Spotify track failed", extra={"track": name, "error": str(e)})
            failed.append(name)
        if progress_callback:
            progress_callback(int((idx + 1) / total * 100) if total else 100)

    logger.info(
        "Spotify CSV complete",
        extra={"downloaded": len(done), "failed": len(failed),
               "without_art": no_art, "dir": playlist_dir},
    )
    return done, failed
