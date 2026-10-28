# Third-party notices

SmuggyConverter is licensed under the GNU Affero General Public License, version 3 or later. See [`LICENSE`](LICENSE).

## NumPy

Music analysis uses NumPy 2.4.6 under its BSD-3-Clause licence. Its complete licence text, including notices for binaries bundled within the NumPy wheel, is included at [`licenses/NumPy-LICENSE.txt`](licenses/NumPy-LICENSE.txt).

## FFmpeg

Windows releases bundle `ffmpeg.exe` and `ffprobe.exe` from Gyan.dev's FFmpeg 8.0.1 essentials build. The binaries identify themselves as `8.0.1-essentials_build-www.gyan.dev`, configured with `--enable-gpl --enable-version3`; they are therefore distributed under GPL-3.0-or-later. A copy of the GNU GPL v3 is included at [`licenses/FFmpeg-GPL-3.0.txt`](licenses/FFmpeg-GPL-3.0.txt).

Corresponding FFmpeg source: <https://github.com/FFmpeg/FFmpeg/tree/894da5ca7d>. The binary release and build details are available at <https://github.com/GyanD/codexffmpeg/releases/tag/8.0.1>. macOS builds fetch separately pinned FFmpeg binaries during CI; their upstream release and exact checksums are recorded in `.github/workflows/release.yaml`.

Other bundled dependencies retain their upstream licence terms. Their pinned package names are listed in `requirements.txt`.
