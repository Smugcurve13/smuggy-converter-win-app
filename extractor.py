import yt_dlp
import json
import datetime

def extract_playlist_info(url):
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "ignoreerrors": True,
    }
    final_array = []
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
                    beech_ka_array = []
                    beech_ka_array.append(f"https://www.youtube.com/watch?v={entry['id']}")
                    beech_ka_array.append(entry.get("title", "Unknown"))
                    time = str(datetime.timedelta(seconds=entry.get("duration", 0)))
                    beech_ka_array.append(time)
                    final_array.append(beech_ka_array)
        #     print(final_array)
        
        # with open("test/playlist_info.json", "w", encoding="utf-8") as f:
        #     f.write(json.dumps(final_array, indent=4))
        return playlist_title, final_array
    except Exception as e:
        print(f"Failed to extract playlist: {e}")
        return {
            "error": str(e)
        }
    
if __name__ == "__main__":
    test_url = "https://youtube.com/playlist?list=PLVbLhzs-GWDkgYKkvn0g96K5HuccMd7yH&si=1_n89kCKwVBMD0bQ"
    info = extract_playlist_info(test_url)
    print(info)