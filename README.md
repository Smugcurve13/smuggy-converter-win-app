# SmuggyConverter

A desktop app for downloading media and converting it to MP3 or MP4. Built with
Python and PySide6, it wraps yt-dlp and FFmpeg behind a GUI so you don't have to
touch a command line.

Runs on **Windows** and **macOS (Apple Silicon)**.

## What it does

| Source | Formats | Notes |
|---|---|---|
| **YouTube video** | MP3, MP4 | Single URL |
| **YouTube playlist** | MP3, MP4 | Pick which videos to download from a searchable list |
| **Spotify playlist** | MP3 | Via an [exportify.net](https://exportify.net) CSV — each track is matched on YouTube and tagged with Spotify's own metadata |
| **Instagram** | MP3, MP4 | Public reels and posts. Carousels save every video |

- **MP3 files are properly tagged** — title, artist, album, year and embedded cover art.
- **MP4 up to 4K** — 2160p, 1440p, 1080p, 720p, 480p. Files are remuxed rather than
  re-encoded, so a download finishes in seconds instead of minutes.
- **FFmpeg is bundled** on Windows and macOS releases; nothing to install.
- **Updates itself** — checks GitHub on launch and, if you say yes, downloads and
  installs the new version in place, then restarts. Nothing to re-download by hand.
- **Progress bar and real error messages**, with a one-click **Export Logs** button
  that zips everything needed to diagnose a problem.

### A note on 4K

YouTube does not offer H.264 above 1080p, so 1440p and 2160p come out as **AV1**.
At 1080p and below you get H.264 + AAC, which plays anywhere. AV1 needs a recent
player — Windows 11, or Windows 10 with the free *AV1 Video Extension* from the
Microsoft Store. Expect 130–250 MB for a 3–4 minute 4K video.

## Download

1. Go to the [Releases](https://github.com/Smugcurve13/smuggy-converter-win-app/releases) page.
2. Grab the asset for your platform:
   - `SmuggyConverter-windows-<version>.zip`
   - `SmuggyConverter-macos-arm64-<version>.zip`
3. Extract it anywhere and run the app. No Python, no FFmpeg install.

**Windows** may warn "Windows protected your PC" — the executable is unsigned.
Click **More info → Run anyway**.

**macOS** builds are ad-hoc signed, not notarised. If Gatekeeper blocks it,
right-click the app → **Open**, or run
`xattr -dr com.apple.quarantine /path/to/SmuggyConverter.app`.

## Using it

1. Pick a mode: **YT Video**, **YT Playlist**, **Spotify** or **Instagram**.
2. Set the output folder (asked once on first run, changeable any time).
3. Paste a URL — or for Spotify, browse to your Exportify CSV.
4. Choose format and quality, then **Convert and Download**.

### Spotify mode

Spotify has no public audio API, so the track list comes from a CSV:

1. Go to [exportify.net](https://exportify.net) and sign in with Spotify.
2. Export the playlist you want as CSV.
3. Select that CSV in the app.

Each track is searched on YouTube, downloaded as MP3, then tagged with the
metadata from your CSV — so you get the real title, artist, album and album art
rather than whatever the YouTube upload was called. Album art missing from the
CSV is fetched from Spotify's public oEmbed endpoint.

## Build it yourself

### Prerequisites

- Python 3.12 (3.9+ should work; CI uses 3.12)
- FFmpeg — bundled in `assets/ffmpeg/windows/` for Windows. On macOS/Linux the app
  falls back to whatever `ffmpeg` is on your `PATH` (`brew install ffmpeg`,
  `apt install ffmpeg`). It refuses to start with a clear message if it finds none.

### Setup

```bash
python -m venv venv
```

Activate it — `venv\Scripts\activate` on Windows, `source venv/bin/activate` on
macOS/Linux — then:

```bash
pip install -r requirements.txt
```

Run from source:

```bash
python main.py
```

### Checks

```bash
python config.py
```

Prints the resolved FFmpeg paths and asserts the platform logic.

```bash
python tests/test_format_selection.py
```

Verifies MP4 quality selection offline, against YouTube's real format ladder — no
network needed. It guards a subtle failure where asking for 4K silently returned
1080p.

### Packaging

CI does this on tag push; see [.github/workflows/release.yaml](.github/workflows/release.yaml).
To build locally:

**Windows**

```bash
pyinstaller main.py --onedir --windowed --clean --name "SmuggyConverter" --icon=assets/icon.ico --add-binary "assets/ffmpeg/windows/ffmpeg.exe;assets/ffmpeg/windows" --add-binary "assets/ffmpeg/windows/ffprobe.exe;assets/ffmpeg/windows" --add-data "assets/logo.png;assets" --add-data "assets/ref.png;assets"
```

**macOS** — same idea, but `:` instead of `;` as the `--add-data` separator, and
point `--add-binary` at arm64 FFmpeg binaries.

Output lands in `dist/`. `--onedir` is deliberate: `--onefile` unpacks ~200 MB of
FFmpeg to a temp directory on every launch, which is slow.

## Releasing

Push a tag matching `v*.*.*`:

```bash
git tag -a v1.3.0 -m "…" && git push origin v1.3.0
```

That builds both platforms and publishes a GitHub Release with both zips
attached. Use the **Run workflow** button on the Actions tab to build a branch
without publishing anything.

> Tags not matching `v*.*.*` do not trigger a release — which is how test builds
> are published without taking the "Latest" badge.

## Logs

Written to `~/.SmuggyConverter/logs/smuggyconverter.log`, rotated daily, 30 days
kept. On Windows that's `C:\Users\<you>\.SmuggyConverter\logs\`.

The **Open Logs Folder** button takes you there; **Export Logs** (offered on any
failure) zips them for sharing. Each run records the app version, yt-dlp version,
Python version and resolved FFmpeg path, which is usually enough to identify a
problem without any back and forth.

## Troubleshooting

**"FFmpeg not found" on startup** — bundled builds shouldn't hit this; if you're
running from source, install FFmpeg (`brew install ffmpeg` /
`apt install ffmpeg`) or put `ffmpeg.exe` and `ffprobe.exe` in
`assets/ffmpeg/windows/`.

**A download fails with HTTP 403** — YouTube rate-limiting. Wait a minute and
retry. Playlist and Spotify batches already pace themselves to avoid it.

**"Sign in to confirm you're not a bot"** — the same thing, more aggressive.
It clears on its own.

**An Instagram post won't download** — only public posts are supported. Private
or login-walled posts report that explicitly.

**Spotify tracks download but tags are empty** — Exportify has changed its column
names across versions. The parser accepts several spellings, but if yours produces
blank tags please open an issue with the CSV's header row.

**4K file won't play** — that's AV1; see the note above. If a 4K request produces
a 1080p file, that *is* a bug worth reporting.

**Downloads fail generally** — click **Export Logs** and check
`smuggyconverter.log`; the error is recorded with its full context. Updating
yt-dlp (`pip install --upgrade yt-dlp`) fixes most extraction breakage, since
sites change constantly.

## Project layout

| Path | Purpose |
|---|---|
| `main.py` | Entry point, startup FFmpeg check |
| `downloader.py` | The only module that downloads anything |
| `playlist.py` | YouTube playlist extraction |
| `spotify.py` | Exportify CSV parsing, metadata and cover art |
| `instagram.py` | Instagram posts, reels and carousels |
| `config.py` | Paths and platform-aware FFmpeg resolution |
| `logs.py` | Logging setup and log export |
| `updater.py` | Release polling, download and the on-restart app swap |
| `gui/` | PySide6 window and dialogs |
| `core/` | Background download and update workers |

## Author

Smugcurve13 (2026)
