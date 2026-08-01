"""Spotify playlist downloads via an Exportify CSV.

Spotify has no public audio API, so the track list comes from a CSV exported at
https://exportify.net and each track is matched on YouTube Music. Spotify's own
metadata then overwrites whatever YouTube supplied, which is the whole point -
YouTube titles like "Song (Official Video)" make for bad library tags.
"""

import csv
import os
import urllib.request

from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TPE2, TPOS, TRCK
from mutagen.mp3 import MP3

from downloader import download_and_convert
from file_utils import MEDIA_DIR, sanitize_filename
from logs import logger

# Exportify column -> our key. Anything missing is simply absent from the track.
_COLUMNS = {
    "Track Name": "track",
    "Artist Name(s)": "artists",
    "Album Name": "album",
    "Album Artist Name(s)": "album_artists",
    "Album Release Date": "release_date",
    "Album Image URL": "image_url",
    "Disc Number": "disc",
    "Track Number": "track_no",
}


def read_exportify_csv(path):
    """Parse an Exportify CSV into a list of track dicts. Rows without a name are skipped."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")

    tracks = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            track = {key: (row.get(col) or "").strip() for col, key in _COLUMNS.items()}
            if not track["track"]:
                continue
            tracks.append(track)

    if not tracks:
        raise ValueError(
            "No tracks found. Is this an Exportify CSV? Expected a 'Track Name' column."
        )
    logger.info("Exportify CSV parsed", extra={"path": path, "tracks": len(tracks)})
    return tracks


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
    """Overwrite the file's ID3 tags with Spotify's metadata."""
    audio = MP3(mp3_path, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()
    tags = audio.tags

    # Replace rather than append, so YouTube's tags don't linger alongside Spotify's.
    for frame in ("TIT2", "TPE1", "TALB", "TPE2", "TDRC", "TRCK", "TPOS", "APIC"):
        tags.delall(frame)

    tags.add(TIT2(encoding=3, text=track["track"]))
    if track["artists"]:
        tags.add(TPE1(encoding=3, text=track["artists"]))
    if track["album"]:
        tags.add(TALB(encoding=3, text=track["album"]))
    if track["album_artists"]:
        tags.add(TPE2(encoding=3, text=track["album_artists"]))
    if track["release_date"]:
        tags.add(TDRC(encoding=3, text=track["release_date"]))
    if track["track_no"]:
        tags.add(TRCK(encoding=3, text=track["track_no"]))
    if track["disc"]:
        tags.add(TPOS(encoding=3, text=track["disc"]))
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

    done, failed = [], []
    total = len(tracks)
    for idx, track in enumerate(tracks):
        name = f"{track['track']} - {track['artists']}" if track["artists"] else track["track"]
        try:
            # ytsearch1 picks the top match; YouTube Music tends to rank the real
            # track above covers and lyric videos for "<title> <artist>".
            query = f"{track['track']} {track['artists']}".strip()
            filename = download_and_convert(
                f"ytsearch1:{query}",
                "mp3",
                quality,
                target_dir=playlist_dir,
                title=name,
            )
            _embed_metadata(
                os.path.join(playlist_dir, filename), track, _fetch_cover(track["image_url"])
            )
            done.append(filename)
        except Exception as e:
            logger.error("Spotify track failed", extra={"track": name, "error": str(e)})
            failed.append(name)
        if progress_callback:
            progress_callback(int((idx + 1) / total * 100) if total else 100)

    logger.info(
        "Spotify CSV complete",
        extra={"downloaded": len(done), "failed": len(failed), "dir": playlist_dir},
    )
    return done, failed
