import os
import sqlite3
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError


def init_db(db_path='file_info.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filetitle TEXT,
            archive_id TEXT
        )'''
        )
    conn.commit()
    cursor.close()
    conn.close()

def store_file_info(original_filetitle, archive_id, db_path='file_info.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO files (original_filetitle, archive_id)
        VALUES (?, ?)
        ''', (original_filetitle, archive_id)
        )
    conn.commit()
    cursor.close()
    conn.close()

def download_audios(channels,download_dir):
    init_db()
    for channel in channels.keys():
        audio_files_dir = os.path.join(download_dir, channel)
        archive_path = os.path.join(
            audio_files_dir, "archive")
        ydl_opts = {
            'outtmpl': os.path.join(audio_files_dir, '%(id)s.%(ext)s'), 
            'format': 'bestaudio[ext=m4a]/bestaudio', 
            'download_archive': archive_path,  
            'playlistend': channels[channel]['plist_end'],
            'ignoreerrors':True,
        }
        playlists = channels[channel]["plists"]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for url in playlists:
                try:
                    info_dict = ydl.extract_info(url, download=True)                    
                    if 'entries' in info_dict:
                        # It's a playlist
                        for entry in info_dict['entries']:
                            process_entry(
                                entry, audio_files_dir,
                                kp_yt_chn_nm=channels[channel]["kp_yt_chn_nm"]
                            )                     
                    else:
                        # It's a single video
                        process_entry(
                            info_dict, audio_files_dir,
                            kp_yt_chn_nm=channels[channel]["kp_yt_chn_nm"]
                        )
                except (DownloadError, ExtractorError) as e:
                    print(f"Error downloading {url}: {e}")

def process_entry(entry, audio_files_dir,kp_yt_chn_nm=False):
    if entry:
        if kp_yt_chn_nm:
            original_filetitle = entry['channel'] + ' ' + entry['title']
        else:
            original_filetitle = entry['title']
        archive_id = entry['id']
        new_filename = os.path.join(audio_files_dir, f'{archive_id}')
        store_file_info(original_filetitle, archive_id)
        print(f"Downloaded and saved as {new_filename}")
        return 0
    else:
        print("Exists error downloading")                      