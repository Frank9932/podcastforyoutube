import os
import yt_dlp
from src.utlis import process_subtitle
from yt_dlp.utils import DownloadError, ExtractorError


def download_audios(channels, dir):
    metadata_list=[]
    archive_path = os.path.join(dir, os.path.pardir, "archive.txt")
    for channel in channels.keys():
        ydl_opts = {
            'outtmpl': os.path.join(dir, '%(id)s.%(ext)s'),
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'download_archive': archive_path,
            'playlistend': channels[channel]['plist_end'],
            'ignoreerrors':True,
            'writesubtitles':True,
        }
        playlists = channels[channel]["plists"]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for url in playlists:
                try:
                    info_dict = ydl.extract_info(url, download=True)           
                    if 'entries' in info_dict:
                        # It's a playlist
                        for entry in info_dict['entries']:
                            process_entry(channel,metadata_list,entry, dir)
                    else:
                        # It's a single video
                        process_entry(channel,metadata_list,info_dict, dir)
                except (DownloadError, ExtractorError) as e:
                    print(f"Error downloading {url}: {e}")
    return metadata_list

def process_entry(channel, metadata_list, entry, files_dir):
    if entry:
            try:
                archive_id = entry['id']
                _file_path = os.path.join(files_dir,f'{archive_id}')
                audio_file_path = f'{_file_path}.m4a'
                subtitle_file_path = f'{_file_path}.zh-Hant.vtt'
                
                yt_channel = entry['channel']
                utime = entry['timestamp']
                ctime = int(os.path.getctime(audio_file_path))
                file_size = os.path.getsize(audio_file_path)
                file_title = entry['title']
                text_content = process_subtitle(subtitle_file_path)
                
                metadata_list.append(
                    [
                        archive_id,
                        channel,
                        yt_channel,
                        utime,
                        ctime,
                        file_size,
                        file_title,
                        text_content
                    ]
                )
            except FileExistsError:
                print('FileExistsError, download timeout')
    else:
        print("some video not available")