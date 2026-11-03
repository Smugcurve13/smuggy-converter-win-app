"""Canonical release notes for the app and GitHub releases."""

import argparse


NOTES = {
    "1.5.3": {
        "NEW": [],
        "CHANGED": [
            "Updated yt-dlp core to v2026.10.26.",
        ],
        "FIXED": [],
    },
    "1.5.2": {
        "NEW": [],
        "CHANGED": [],
        "FIXED": [
            "The update prompt now stays open when you choose What’s New, so Update Now remains available.",
        ],
    },
    "1.5.1": {
        "NEW": [],
        "CHANGED": [],
        "FIXED": [
            "Choosing What’s New from the update prompt now keeps the update prompt available when you return.",
        ],
    },
    "1.5.0": {
        "NEW": [
            "Analyze Music scans a local folder for estimated BPM, musical key, and Camelot key, then exports the results as CSV.",
            "MP4 downloads can now be center-cropped to Square, Portrait, or Reel dimensions.",
        ],
        "CHANGED": [
            "The app now keeps one easy-to-open smuggyconverter.log file; legacy text logs are consolidated once and removed.",
            "Open Logs Folder is now Open Log and opens the current log file directly.",
        ],
        "FIXED": [
            "Playlist completion now names the playlist and reports tracks already downloaded instead of calling a fully skipped repeat successful.",
            "A playlist already downloaded with the same folder, format, and quality now warns before track selection.",
        ],
    },
    "1.5.0-alpha.1": {
        "NEW": [
            "Analyze Music scans a local folder for BPM, musical key, and Camelot key, then exports the results as CSV.",
        ],
        "CHANGED": [],
        "FIXED": [
            "SmuggyConverter no longer adds a macOS menu-bar icon.",
        ],
    },
    "1.4.0": {
        "NEW": [
            "First-launch onboarding and an in-app What's New dialog.",
            "Remembered mode, format, per-format quality, and output folder preferences.",
            "Optional last-URL retention, disabled by default.",
            "Spotify Exportify guidance, live conversion status, safe cancellation, and retry for failed batch items.",
        ],
        "CHANGED": [
            "Playlist rows known to be private or deleted stay visible but cannot be selected.",
            "Completion dialogs now distinguish completed, completed with issues, failed, and cancelled runs.",
            "GitHub releases use these same categorized notes shown in the app.",
        ],
        "FIXED": [
            "Failed and unfinished batch items no longer prevent completed items from being retained for resume.",
            "Instagram access errors now explain public/private/deleted/sign-in cases clearly.",
            "Mix/radio YouTube links now resolve to one video in Video mode, while list-only links switch to Playlist mode.",
            "Getting Started and What's New are separate, larger, readable dialogs.",
        ],
    }
}


def get_notes(version):
    return NOTES.get(version, {})


def render_markdown(version):
    notes = get_notes(version)
    if not notes:
        return ""
    sections = [f"# SmuggyConverter v{version}"]
    for category in ("NEW", "CHANGED", "FIXED"):
        entries = notes.get(category, [])
        if entries:
            sections.append(f"## {category.title()}\n" + "\n".join(f"- {entry}" for entry in entries))
    return "\n\n".join(sections) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    args = parser.parse_args()
    rendered = render_markdown(args.version)
    if not rendered:
        raise SystemExit(f"No release notes for {args.version}")
    print(rendered, end="")


if __name__ == "__main__":
    main()
