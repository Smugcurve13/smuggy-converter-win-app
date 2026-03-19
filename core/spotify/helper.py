import yt_dlp
import requests
import os
import shutil
from mutagen.mp3 import MP3
from mutagen.id3._frames import APIC, TALB, TPE1, TPE2, TDRC, TRCK, TPOS, TIT2
from mutagen.id3 import ID3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
import csv
import re
import typing

from config.logs import logger
from config.file_utils import MEDIA_DIR
from config.config import FFMPEG_PATH, FFPROBE_PATH

settings = {
    'format': 'mp3',
    'output_path': MEDIA_DIR,
    'cookie_file': None,
    'platform': 'ytmusic'
}

def sanitize_string(string: str) -> str:
    """Removes illegal characters from a filename."""
    return re.sub(r'[<>:"/\\|?*]', '_', string)

def read_exportify_csv_file(file_path: str) -> list:
    """Reads an Exportify CSV file and returns its content as a list of dictionaries."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    with open(file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        songs_list = [ row for row in reader ]
        
    for song in songs_list:
        try:
            song['track_name'] = sanitize_string(song['Track Name'])
            song['artist_names'] = [sanitize_string(artist) for artist in song['Artist Name(s)'].split(',')]
            song['album_name'] = sanitize_string(song['Album Name'])
            song['album_artist_names'] = [sanitize_string(artist) for artist in song['Album Artist Name(s)'].split(',')]
            song['album_release_date'] = song['Album Release Date']
            song['album_image_url'] = song['Album Image URL']
            song['disc_number'] = song['Disc Number']
            song['track_number'] = song['Track Number']
            song['track_duration_ms'] = int(song['Track Duration (ms)']) if song['Track Duration (ms)'].isdigit() else 0
            
            keys_to_remove = [
                "Track URI", "Artist URI(s)", "Album URI", "Album Artist URI(s)",
                "Track Preview URL", "Explicit", "Popularity", "ISRC", "Added By", "Added At",
                "Track Name", "Artist Name(s)", "Album Name", "Album Artist Name(s)", "Album Release Date",
                "Album Image URL", "Disc Number", "Track Number", "Track Duration (ms)"

            ]
            
            for key in keys_to_remove:
                    del song[key]
        except Exception as e:
            logger.info(f"Some error occurred when handling metadata for song {song['track_name']}, error {e} skipping the song.")
            continue

    return songs_list

def embed_spotify_metadata_mutagen(audiofile, image_file_path, metadata, format: typing.Literal["mp3", "m4a", "flac"]):
    try:
        if format == "mp3":
            audio = MP3(audiofile, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            
            # linter keeps crying about this
            assert audio.tags is not None
            
            if image_file_path and os.path.exists(image_file_path):
                with open(image_file_path, 'rb') as art:
                    audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=art.read()))
            
            track_name = metadata['track_name']
            artist_names_str = ', '.join(metadata['artist_names'])

            audio.tags.add(TIT2(encoding=3, text=track_name))
            audio.tags.add(TPE1(encoding=3, text=artist_names_str))
            if metadata.get('album_name'):
                audio.tags.add(TALB(encoding=3, text=metadata['album_name']))
            if metadata.get('album_artist_names'):
                audio.tags.add(TPE2(encoding=3, text=', '.join(metadata['album_artist_names'])))
            if metadata.get('album_release_date'):
                audio.tags.add(TDRC(encoding=3, text=metadata['album_release_date']))
            if metadata.get('track_number'):
                audio.tags.add(TRCK(encoding=3, text=str(metadata['track_number'])))
            if metadata.get('disc_number'):
                audio.tags.add(TPOS(encoding=3, text=str(metadata['disc_number'])))
            
            audio.save()

        elif format == "m4a":
            audio = MP4(audiofile)
            
            if audio.tags is None:
                audio.add_tags()
            
            assert audio.tags is not None

            if image_file_path and os.path.exists(image_file_path):
                with open(image_file_path, 'rb') as art:
                    audio.tags['covr'] = [MP4Cover(art.read(), MP4Cover.FORMAT_JPEG)]
            
            track_name = metadata['track_name']
            artist_names_str = ', '.join(metadata['artist_names'])

            audio.tags['\xa9nam'] = [track_name]
            audio.tags['\xa9ART'] = [artist_names_str]
            if metadata.get('album_name'):
                audio.tags['\xa9alb'] = [metadata['album_name']]
            if metadata.get('album_artist_names'):
                audio.tags['aART'] = [', '.join(metadata['album_artist_names'])]
            if metadata.get('album_release_date'):
                audio.tags['\xa9day'] = [metadata['album_release_date']]
            if metadata.get('track_number'):
                audio.tags['trkn'] = [(int(metadata['track_number']), 0)]
            if metadata.get('disc_number'):
                audio.tags['disk'] = [(int(metadata['disc_number']), 0)]
            
            audio.save()

        elif format == "flac":
            audio = FLAC(audiofile)
            
            if audio.tags is None:
                audio.add_tags()
            
    
            if image_file_path and os.path.exists(image_file_path):
                with open(image_file_path, 'rb') as art:
                    picture = Picture()
                    picture.type = 3
                    picture.mime = 'image/jpeg'
                    picture.desc = 'Cover'
                    picture.data = art.read()
                    audio.add_picture(picture)
            
            track_name = metadata['track_name']
            artist_names_str = ', '.join(metadata['artist_names'])
            
            
            assert audio.tags is not None

            audio.tags['TITLE'] = [track_name] # type: ignore
            audio.tags['ARTIST'] = [artist_names_str] # type: ignore
            if metadata.get('album_name'):
                audio.tags['ALBUM'] = [metadata['album_name']] # type: ignore
            if metadata.get('album_artist_names'):
                audio.tags['ALBUMARTIST'] = [', '.join(metadata['album_artist_names'])] # type: ignore
            if metadata.get('album_release_date'):
                audio.tags['DATE'] = [metadata['album_release_date']] # type: ignore
            if metadata.get('track_number'):
                audio.tags['TRACKNUMBER'] = [str(metadata['track_number'])] # type: ignore
            if metadata.get('disc_number'):
                audio.tags['DISCNUMBER'] = [str(metadata['disc_number'])] # type: ignore
            
            audio.save()

    except Exception as e:
        track_name = metadata.get('track_name', 'Unknown')
        print(f"An error occurred during metadata embedding for track {track_name}: {e}")


def download_spotify_song(format: typing.Literal["mp3", "flac", "m4a"], metadata, output_path='.', cookiefile=None, platform="youtube"):
    if metadata is None:
        print("no song metadata, skipping song...")
        return

    # metadata
    track_name = metadata.get('track_name', 'Unknown Track')
    artist_names = metadata.get('artist_names', ['Unknown Artist'])
    image_url = metadata.get('album_image_url')
    artist_names_str = ', '.join(artist_names)
    
    # final naming
    final_audio_file_path = os.path.join(output_path, f"{track_name} - {artist_names_str}.{format}")
    
    if os.path.exists(final_audio_file_path):
        print(f"File {final_audio_file_path} already exists. Skipping download.")
        return
    
    image_file_path = os.path.join(output_path, "temp_cover.jpg")

    # getting the image
    if image_url:
        try:
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            with open(image_file_path, 'wb') as out_file:
                for chunk in response.iter_content(chunk_size=8192):
                    out_file.write(chunk)
        except requests.exceptions.RequestException as e:
            print(f"WARNING : Error downloading image for track {track_name}: {e}")
            image_file_path = None
    else:
        image_file_path = None

    search_query = f"{track_name} by {artist_names}"
    
    if platform == "ytmusic":
        search_input = f"https://music.youtube.com/search?q={search_query.replace(' ', '+')}"
    else:
        search_input = f"ytsearch1:{search_query}"
    
    temp_filename = f"{track_name} - {artist_names_str}"
 
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, f'{temp_filename}.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': format,
            'preferredquality': '0',
        }],
        'ffmpeg_location': FFMPEG_PATH,
        'verbose': False,
        'playlist_items': '1',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
        'cookiefile': cookiefile,
    }

    # audio download
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([search_input])

        downloaded_file_path = os.path.join(output_path, f"{temp_filename}.{format}")
        
        if not os.path.exists(downloaded_file_path):
            raise Exception(f"Expected downloaded file not found at {downloaded_file_path}")

    except Exception as e:
        print(f"\nAn error occurred during audio download for the track {track_name}: {e}")
        if image_file_path and os.path.exists(image_file_path):
            os.remove(image_file_path)
        return

    # embedding metadata and album image
    if downloaded_file_path and os.path.exists(downloaded_file_path):
        embed_spotify_metadata_mutagen(downloaded_file_path, image_file_path, metadata, format)
        
        if os.path.exists(downloaded_file_path):
            shutil.move(downloaded_file_path, final_audio_file_path)
    
    # clean up
    if image_file_path and os.path.exists(image_file_path):
        os.remove(image_file_path)


def download_spotify_songs_from_list(songs, platform):
    """Download Spotify songs with full metadata"""
    
    total_songs = len(songs)
    logger.info(f"Starting download of {total_songs} Spotify songs with metadata...")
    
    for i, song in enumerate(songs):
        try:
            track_name = song.get('track_name', 'Unknown')
            artists = ', '.join(song.get('artist_names', ['Unknown']))
            logger.info(f"[{i+1}/{total_songs}] Downloading: {track_name} by {artists}")
            
            download_spotify_song(settings['format'], song, settings['output_path'], settings['cookie_file'], platform)
            try:
                logger.info(f"✓ Successfully downloaded: {track_name}")
            except UnicodeEncodeError:
                logger.info(f"Successfully downloaded: {track_name}")
            
        except Exception as e:
            try:
                logger.info(f"✗ Failed to download {track_name}: {e}")
            except UnicodeEncodeError:
                logger.info(f"Failed to download {track_name}: {e}")
            continue
    
    logger.info("All Spotify downloads complete!")


def process_exportify_csv(file_path):
    """Download using Exportify CSV file"""
            
    if not os.path.exists(file_path):
        logger.info("File not found!")

        return
    
    logger.info("Reading CSV file...")
    try:
        songs = read_exportify_csv_file(file_path)
        logger.info("Processing songs...")
        
        if songs:
            download_spotify_songs_from_list(songs, settings['platform'])
        else:
            logger.info("No songs found in the CSV file")
        
    except Exception as e:
        logger.info(f"Error: {e}")

if __name__ == "__main__":
    # Example usage: process_exportify_csv("path_to_exportify_file.csv")
    process_exportify_csv(r"c:\Users\ADMIN\Downloads\hype.csv")