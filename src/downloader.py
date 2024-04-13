import datetime
import os
import subprocess


def remove_old_files(_dir):
    current_date = datetime.date.today()
    past_date = current_date - datetime.timedelta(days=14)
    try:
        for root, dirs, files in os.walk(_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_date = datetime.date.fromtimestamp(
                    os.path.getmtime(file_path))
                if file_date < past_date and file.endswith(".mp3"):
                    os.remove(file_path)
    finally:
            return

def download_files(config_dic):
    data_dir = "data"
    for show_name in config_dic.keys():
        audio_files_dir = os.path.join(data_dir, show_name)
        archive_location = os.path.join(
            data_dir, audio_files_dir, f"archive_{show_name}"
            )
        playlists = config_dic[show_name]
        for playlist in playlists:
            subprocess.run(
            [
                "yt-dlp",
                "-x",
                "--audio-format",
                "mp3",
                "-o",
                "%(channel)s_%(title)s.%(ext)s",
                "--paths",
                audio_files_dir,
                "--download-archive",
                archive_location,
                playlist,
                "--playlist-end",
                "1"
            ]
        )

if __name__ == "__main__":
    data_dir = "/var/www/podcast/youtube_channels/"