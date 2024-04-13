from requests import post
import json
import datetime
import os
import subprocess
import time
import html

def send_msg(msg):
    tg_configure_path="config/secrets.json"    
    tg_configure = json.load(open(tg_configure_path))
    token = tg_configure["tg"]["token"]
    chat_id = tg_configure["tg"]["chat_id"]
    r = post(
        f'https://api.telegram.org/bot{token}/sendMessage', 
        json={"chat_id": chat_id, "text": msg}
        )

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

def rename_file_by_dir(dir):
    for filename in os.listdir(dir):
        if filename.endswith(".mp3"):
            new_filename = filename.replace("&", "_")
            new_filename = new_filename.replace("#", "-")
            os.rename(
                os.path.join(dir, filename),
                os.path.join(dir, new_filename)
                )

def create_rss_file(show_name, web_dir):
    data_dir = "data"
    update_list = []
    files = []
    archive_list = []

    show_web_dir = os.path.join(web_dir, show_name)
    audio_files_dir = os.path.join(data_dir, show_name)
    for filename in os.listdir(audio_files_dir):
        filepath = os.path.join(audio_files_dir, filename)
        if os.path.isfile(filepath) and filename.lower().endswith(('.mp3', '.m4a', '.aac')):
            name = os.path.splitext(filename)[0]
            item = {
                'path': filepath,
                'name': html.escape(name),
                'fname': html.escape(filename),
                'time': os.path.getctime(filepath),
                'length': os.path.getsize(filepath)
            }
            files.append(item)
        
    files = sorted(files, key=lambda x: x['time'], reverse=True)

    rss_output = '<?xml version="1.0" encoding="UTF-8"?>\n' \
                 '<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">\n' \
                 '  <channel>\n' \
                 f'    <title>{html.escape(show_name)}</title>\n' \
                 f'    <itunes:image href="{html.escape(show_web_dir)}img.jpg" />\n'
    
    for item in files:
        url = show_web_dir + item['fname']
        mime = 'audio/mpeg' if item['fname'].endswith('.mp3') else 'audio/mp4'
    
        pub_date = time.strftime('%a, %d %b %Y %H:%M:%S %z', time.localtime(item['time']))
        
        rss_output += f'    <item>\n' \
                      f'      <title>{item["name"]}</title>\n' \
                      f'      <enclosure url="{html.escape(url)}" length="{item["length"]}" type="{mime}" />\n' \
                      f'      <guid isPermaLink="true">{html.escape(url)}</guid>\n' \
                      f'      <pubDate>{pub_date}</pubDate>\n' \
                      f'    </item>\n'
    
    rss_output += '  </channel>\n' \
                  '</rss>'
                
    with open(os.path.join(data_dir, show_name, "index.rss"), "w", encoding="utf-8") as index_file:
        index_file.write(rss_output)


# def create_rss_file(show_name,web_dir):
#     data_dir = "data"
#     update_list = []
#     files = []
#     archive_list = []

#     show_web_dir = os.path.join(web_dir, show_name)
#     audio_files_dir = os.path.join(data_dir, show_name)
#     for filename in os.listdir(audio_files_dir):
#         filepath = os.path.join(audio_files_dir, filename)
#         if os.path.isfile(filepath) and filename.lower().endswith(('.mp3', '.m4a', '.aac')):
#             name = os.path.splitext(filename)[0]
#             item = {
#                 'path': filepath,
#                 'name': name,
#                 'fname': filename,
#                 'time': os.path.getctime(filepath),
#                 'length': os.path.getsize(filepath)
#             }
#             files.append(item)
        
#     files = sorted(files, key=lambda x: x['time'])

#     rss_output = '<?xml version="1.0" encoding="utf-8"?>\n' \
#                     '<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">\n' \
#                     '  <channel>\n' \
#                     f'    <title>{show_name}</title>\n' \
#                     f'    <itunes:image href="{show_web_dir}img.jpg" />\n'
        
#     for item in files:
#         url = show_web_dir + item['fname']        
#         if item['fname'].endswith('.mp3'):
#             mime = 'audio/mp3'
#         elif item['fname'].endswith('.webm'):
#             mime = 'audio/webm'
#         else:
#             mime = 'audio/mp4'
    
#         pub_date = time.strftime('%a, %d %b %Y %H:%M:%S %z', time.localtime(item['time']))
        
#         rss_output += f'    <item>\n' \
#                 f'      <title>{item["name"]}</title>\n' \
#                 f'      <enclosure url="{url}"\n' \
#                 f'                 length="{item["length"]}"\n' \
#                 f'                 type="{mime}" />\n' \
#                 f'      <guid isPermaLink="true">{url}</guid>\n' \
#                 f'      <pubDate>{pub_date}</pubDate>\n' \
#                 f'    </item>\n'
    
#         rss_output += '  </channel>\n' \
#                 '</rss>'
                
#     with open(os.path.join(data_dir, show_name,"index.rss"), "w") as index_file:
#          index_file.write(rss_output)
