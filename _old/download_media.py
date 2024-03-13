import os
import subprocess
import datetime
import user_data 

def download_media(config_dic):
    # local_podcast_location = "/var/www/podcast/youtube_channels/"
    for item in config_dic.keys():
        class_name =   item
        class_location = local_podcast_location + class_name
        archive_location = class_location + "/archive_"+ class_name
        
        # 删除过去日期之前的音频文件
        current_date = datetime.date.today()
        past_date = current_date - datetime.timedelta(days=14)
        try:
            for root, dirs, files in os.walk(class_location):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_date = datetime.date.fromtimestamp(os.path.getmtime(file_path))
                    if file_date < past_date and file.endswith(".mp3"):
                       os.remove(file_path)
        finally :
        # 从指定的频道下载最新的2个视频
            playlists = config_dic[item]
            for playlist in playlists:
                subprocess.run(
                [
                    location_of_yt_dlp,
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



# if __name__ == "__main__":
#     config_dic = {"AINews":["https://www.youtube.com/@JeffTechView/videos"]}
#     download_media(config_dic)

















