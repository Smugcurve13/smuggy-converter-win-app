"""Centered video-crop options for MP4 downloads."""

CROP_OPTIONS = ("Original", "1:1 (Square)", "4:5 (Portrait)", "9:16 (Reel)")

_FILTERS = {
    "1:1 (Square)": "crop=min(iw\\,ih):min(iw\\,ih):(iw-ow)/2:(ih-oh)/2",
    "4:5 (Portrait)": "crop=min(iw\\,ih*4/5):min(ih\\,iw*5/4):(iw-ow)/2:(ih-oh)/2",
    "9:16 (Reel)": "crop=min(iw\\,ih*9/16):min(ih\\,iw*16/9):(iw-ow)/2:(ih-oh)/2",
}


def crop_filter(choice: str) -> str | None:
    if choice == "Original":
        return None
    try:
        return _FILTERS[choice]
    except KeyError as exc:
        raise ValueError(f"Unknown crop option: {choice}") from exc
