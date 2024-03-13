import requests
import json
import datetime
import os
import subprocess


def send_msg(msg):
    configure_path="mod-config.json"    
    mod_configure = json.load(open(configure_path))
    token = mod_configure["tg"]["token"]
    chat_id = mod_configure["tg"]["chat_id"]
    r = requests.post(f'https://api.telegram.org/bot{token}/sendMessage', json={"chat_id": chat_id, "text": msg})

def remove_old_files(config_dic):
    current_date = datetime.date.today()
    past_date = current_date - datetime.timedelta(days=14)
    local_podcast_location = "/var/www/podcast/youtube_channels/"
    for item in config_dic.keys():
        class_name =   item
        class_location = local_podcast_location + class_name
        try:
            for root, dirs, files in os.walk(class_location):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_date = datetime.date.fromtimestamp(os.path.getmtime(file_path))
                    if file_date < past_date and file.endswith(".mp3"):
                        os.remove(file_path)
        finally:
            return

def download_files(config_dic):
    local_podcast_location = "/var/www/podcast/youtube_channels/"
    for item in config_dic.keys():
        class_name =   item
        class_location = local_podcast_location + class_name
        archive_location = class_location + "/archive_"+ class_name
        playlists = config_dic[item]
        for playlist in playlists:
            subprocess.run(
            [
                "/usr/local/bin/yt-dlp",
                "-x",
                "--audio-format",
                "mp3",
                "-o",
                "%(channel)s_%(title)s.%(ext)s",
                "--paths",
                class_location,
                "--download-archive",
                archive_location,
                playlist,
                "--playlist-end",
                "1"
            ]
        )

def rename_file(files_dir):
    for filename in os.listdir(files_dir):
        if filename.endswith(".mp3"):
            # new_filename = filename.replace("[", "【")
            # new_filename = new_filename.replace("]", "】")
            new_filename = filename.replace("&", "_")
            new_filename = new_filename.replace("#", "-")
            os.rename(os.path.join(files_dir, filename),
            os.path.join(files_dir, new_filename))

def rss_generator():
    