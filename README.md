# SmuggyConverter (Windows App)

A lightweight Windows GUI application for downloading online media and converting it to various audio/video formats. Built with Python and PyQt6, SmuggyConverter provides an intuitive interface for fetching media from popular platforms and converting them to your preferred format.

## Features

- **Easy Media Downloads**: Download videos and audio from various online platforms
- **Format Conversion**: Convert downloaded media to multiple audio and video formats
- **Playlist Support**: Download entire playlists with a single click
- **Quality Selection**: Choose your preferred quality for downloads
- **Built-in FFmpeg**: FFmpeg binaries can be bundled with the release for seamless conversion
- **Cross-platform Logging**: Automatic logging system that works across Windows, macOS, and Linux

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

- **Operating System**: Windows 10/11 (primary target), also compatible with macOS/Linux
- **Python**: Python 3.8 or higher
- **Virtual Environment**: (Optional but strongly recommended to avoid dependency conflicts)
- **FFmpeg**: Required for media conversions. Can be:
  - Bundled with the executable (recommended for releases)
  - Installed system-wide and available in PATH
  - Placed in `assets/ffmpeg/windows/` directory

### Setup

1. **Clone or download** this repository to your local machine.

2. **Create a virtual environment** (recommended):
```bash
python -m venv .venv
```

3. **Activate the virtual environment**:
```bash
.venv\\Scripts\\activate
```

4. **Install dependencies**:
```bash
pip install -r requirements.txt
```

5. **Verify FFmpeg** (if not bundling): Ensure FFmpeg is installed and accessible.
```bash
ffmpeg -version
```

### Run from source

Once setup is complete, launch the application:

```bash
python main.py
```

The GUI window should open, allowing you to paste URLs, select formats, and start downloads.

### Build an .exe (PyInstaller)

To create a standalone executable that can run without Python installed:

**Basic Windows build** (without bundled FFmpeg):

```bash
pyinstaller --onefile --windowed --icon=assets/icon.ico --add-data "assets/icon.ico;." --clean --name="SmuggyConverter" main.py
```

**Full build with bundled FFmpeg** (recommended for distribution):

```bash
pyinstaller main.py --onefile --windowed --clean --name "SmuggyConverter" --icon=assets/icon.ico --add-binary "assets/ffmpeg/windows/ffmpeg.exe;assets/ffmpeg/windows" --add-binary "assets/ffmpeg/windows/ffprobe.exe;assets/ffmpeg/windows" --add-data "assets/logo.png;assets" --add-data "assets/ref.png;assets"
```

The built executable will be located in the `dist/` directory.

**Note**: Building with `--onefile` creates a single executable but may take longer to start. For faster startup, omit `--onefile` to create a folder distribution.

## Development notes

- Useful PyInstaller/Dev commands are also kept in `cmd.txt`.
- Logs are automatically saved to `~/.SmuggyConverter/logs/logs.txt` for debugging purposes.
- The application uses platform-specific home directory detection (Windows: `%USERPROFILE%`, macOS/Linux: `$HOME`).

## Troubleshooting & Common Issues

### Installation Issues

**Problem**: `pip install -r requirements.txt` fails with dependency errors

**Solutions**:
- Ensure you're using Python 3.8 or higher: `python --version`
- Upgrade pip: `python -m pip install --upgrade pip`
- Try installing dependencies one at a time to identify the problematic package
- If PyQt6 fails, you may need to install Visual C++ Redistributables on Windows

**Problem**: Virtual environment won't activate

**Solutions**:
- On Windows, you may need to enable script execution: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Verify the path: `.venv\Scripts\activate.bat` (CMD) or `.venv\Scripts\Activate.ps1` (PowerShell)

### Runtime Issues

**Problem**: "FFmpeg not found" error when converting

**Solutions**:
- Install FFmpeg system-wide and ensure it's in your PATH
- Place `ffmpeg.exe` and `ffprobe.exe` in `assets/ffmpeg/windows/` directory
- Download FFmpeg from: https://ffmpeg.org/download.html
- Verify installation: `ffmpeg -version` in terminal

**Problem**: Application starts but downloads fail

**Solutions**:
- Check your internet connection
- Verify the URL is valid and from a supported platform
- Check the logs at `~/.SmuggyConverter/logs/logs.txt` for error details
- Some platforms may require authentication or have region restrictions
- Try updating yt-dlp: `pip install --upgrade yt-dlp`

**Problem**: GUI doesn't appear or crashes on startup

**Solutions**:
- Ensure PyQt6 is properly installed: `pip install --force-reinstall PyQt6`
- Check for any Python errors in the terminal
- Verify all asset files (icons, images) are present in the `assets/` directory
- Try running in non-windowed mode to see error messages

**Problem**: Downloaded files have no audio or video

**Solutions**:
- Ensure FFmpeg is properly configured
- Try a different format selection
- Check if the source URL has the desired quality available
- Review logs for FFmpeg conversion errors

**Problem**: Executable won't run ("Windows protected your PC" error)

**Solutions**:
- This is normal for unsigned executables. Click "More info" then "Run anyway"
- To avoid this, you can sign the executable (requires a code signing certificate)
- Users can add an exception in Windows Security

### Building Issues

**Problem**: PyInstaller build fails

**Solutions**:
- Clear previous builds: `rmdir /s dist build` and delete `.spec` files
- Install/upgrade PyInstaller: `pip install --upgrade pyinstaller`
- Try building without `--onefile` first to diagnose issues
- Check that all paths in `--add-data` and `--add-binary` exist

**Problem**: Built executable is too large

**Solutions**:
- Use virtual environment to minimize dependencies
- Consider using `--exclude-module` for unused packages
- Don't bundle FFmpeg if users can install it separately
- Use UPX compression (add `--upx-dir` option)

**Problem**: Executable runs but assets are missing

**Solutions**:
- Verify `--add-data` paths in the PyInstaller command
- Check the separator: use `;` on Windows, `:` on macOS/Linux
- Ensure assets exist before building
- Test the executable from a different directory than the build location

### Logging & Debugging

- **Log Location**: `~/.SmuggyConverter/logs/logs.txt`
  - Windows: `C:\Users\YourUsername\.SmuggyConverter\logs\logs.txt`
  - macOS/Linux: `~/.SmuggyConverter/logs/logs.txt`
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Check Logs For**: Download errors, conversion failures, FFmpeg issues, network problems

### Platform-Specific Notes

**Windows**:
- Use PowerShell or CMD for commands
- Paths use backslashes (`\`) but Python handles forward slashes (`/`) too
- May need administrator privileges for certain operations

**macOS/Linux** (experimental):
- Replace `python` with `python3` if needed
- Activation script: `source .venv/bin/activate`
- FFmpeg: Install via homebrew (macOS) or apt/yum (Linux)
- PyInstaller separator in add-data: use `:` instead of `;`

### Still Having Issues?

1. **Check the logs** at `~/.SmuggyConverter/logs/logs.txt` for detailed error messages
2. **Update dependencies**: `pip install --upgrade -r requirements.txt`
3. **Try a clean reinstall**: Delete `.venv`, recreate it, and reinstall packages
4. **Check TODO.md** for known issues and planned fixes
5. **Verify system requirements** are met (Python version, OS compatibility)

## Author

Smugcurve13 (2026)