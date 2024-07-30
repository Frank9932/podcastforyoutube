import json
from src.utlis import create_rss_file, send_msg,remove_old_files
from src.downloader import download_audios


# load config
with open('./config.json', 'r') as file:
    channels = json.load(file)
# deploy
# data_dir = "/var/www/podcast/youtube_channels/"
# web_dir = "/var/www/podcast/youtube_channels/"
# test
data_dir = "/home/leo/repos/podcastforyoutube/test/"
web_dir = "http://192.168.0.225/podcast/"
# download
download_audios(channels,data_dir)
# removal
remove_old_files(channels,data_dir)
# make index
new_update = create_rss_file(channels,data_dir,web_dir)
print(new_update)