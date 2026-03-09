# SmuggyConverter (Windows App)

A small Windows GUI app for downloading and converting media.

## Download (recommended)

If you just want to use the app:

1. Go to the **Releases** page.
2. Download the latest **.rar** asset.
3. Extract it anywhere.
4. Run the included executable.

> Note: The release archive already contains a built app. You don’t need Python installed to use the release build.

## Build it yourself

If you prefer to build your own executable, you can.

### Prerequisites

- Windows 10/11
- Python 3.x
- (Optional but recommended) a virtual environment
- **ffmpeg** (required for conversions)

### Setup

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

### Run from source

```bash
python main.py
```

### Build an .exe (PyInstaller)

Basic Windows build:

```bash
pyinstaller --onefile --windowed --icon=assets/icon.ico --add-data "assets/icon.ico;." --clean --name="SmuggyConverter" main.py
```

Bundling ffmpeg with the build (optional):

```bash
pyinstaller main.py --onefile --windowed --clean --name "SmuggyConverter" --icon=assets/icon.ico --add-binary "assets/ffmpeg/windows/ffmpeg.exe;assets/ffmpeg/windows" --add-binary "assets/ffmpeg/windows/ffprobe.exe;assets/ffmpeg/windows" --add-data "assets/logo.png;assets" --add-data "assets/ref.png;assets"
```

The built executable will be located under `dist/`.

## Development notes

- Useful PyInstaller/Dev commands are also kept in `cmd.txt`.

## Author

Smugcurve13 (2026)