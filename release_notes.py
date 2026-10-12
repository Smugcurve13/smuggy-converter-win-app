"""Canonical release notes for the app and GitHub releases."""

import argparse


NOTES = {
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
