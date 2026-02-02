import yt_dlp
import json

def extract_playlist_info(url):
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "ignoreerrors": True,
    }
    video_urls = []
    video_titles = []
    playlist_title = "playlist"
    ydl = yt_dlp.YoutubeDL(ydl_opts)
    try:
        info = ydl.extract_info(url, download=False)
        # print(type(info))
        # with open("test/debug_info.json", "w", encoding="utf-8") as f:
        #     f.write(json.dumps(info, indent=4))
        playlist_title = info.get("title", playlist_title)
        if "entries" in info:
            for entry in info["entries"]:
                if entry and "id" in entry:
                    video_urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
                if entry and "title" in entry:
                    video_titles.append(entry["title"])
        return {
            "title": playlist_title,
            "video_urls": video_urls,
            "video_titles": video_titles
        }
    except Exception as e:
        print(f"Failed to extract playlist: {e}")
        return {
            "error": str(e)
        }
    
if __name__ == "__main__":
    test_url = "https://youtube.com/playlist?list=PLVbLhzs-GWDkgYKkvn0g96K5HuccMd7yH&si=1_n89kCKwVBMD0bQ"
    info = extract_playlist_info(test_url)
    print(info)