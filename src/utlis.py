import os
from requests import post
import json
import sqlite3
import datetime
import subprocess
import time
import xml.sax.saxutils as saxutils
import urllib.parse


def send_msg(msg):
    if not msg :
        return
    tg_cfg_path="config/secrets.json"    
    tg_cfg = json.load(open(tg_cfg_path))
    token = tg_cfg["tg"]["token"]
    chat_id = tg_cfg["tg"]["chat_id"]
    r = post(
        f'https://api.telegram.org/bot{token}/sendMessage', 
        json={"chat_id": chat_id, "text": msg}
        )

def remove_old_files(channels,data_dir):
    current_date = datetime.date.today()
    past_date = current_date - datetime.timedelta(days=7)
    for channel in channels.keys():
        if channels[channel]["keep_old"]:
            continue
        show_dir = data_dir + channel
        try:
            for root, dirs, files in os.walk(show_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_date = datetime.date.fromtimestamp(
                        os.path.getmtime(file_path))
                    if file_date < past_date and file.endswith(".m4a"):
                        os.remove(file_path)
        finally:
            pass

def download_files(channels,data_dir):
    for channel in channels.keys():
        audio_files_dir = os.path.join(data_dir, channel)
        archive_location = os.path.join(data_dir, audio_files_dir, "archive")
        playlists = channels[channel]["plist"]
        if channels[channel]["kp_yt_chnl_nm"]:
            file_name = "%(channel)s %(title)s.%(ext)s"
        else:
            file_name = "%(title)s.%(ext)s"
        for playlist in playlists:
            subprocess.run(
                [
                    "yt-dlp",
                    "-x",
                    # "--write-thumbnail",
                    "--audio-format",
                    "mp3",
                    "-o",
                    f"{file_name}",
                    # "-o",
                    # "thumbnail:%(channel)s %(title)s.%(ext)s",
                    "--paths",
                    audio_files_dir,
                    "--download-archive",
                    archive_location,
                    playlist,
                    "--playlist-end",
                    f"{channels[channel]['plist_end']}"
                ]
            )

def fetch_file_by_id(cursor,name):
    cursor.execute('SELECT original_filetitle, archive_id FROM files WHERE archive_id = ?', (name,))
    row = cursor.fetchone()
    return row[0]

def create_rss_file(channels,data_dir,web_dir,db_path='file_info.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    full_update_list =[]
    for channel in channels.keys():
        files = []
        audio_files_dir = os.path.join(data_dir, channel)
        show_web_dir = os.path.join(web_dir, channel)
        tmp=os.listdir(audio_files_dir)
        for filename in os.listdir(audio_files_dir):
            filepath = os.path.join(audio_files_dir, filename)
            if os.path.isfile(filepath) and filename.lower().endswith('.m4a'):
                name = os.path.splitext(filename)[0]
                item = {
                    'path': filepath,                   
                    'name': name,                       
                    'fname': filename,                  
                    'time': os.path.getctime(filepath), 
                    'length': os.path.getsize(filepath) 
                }
                files.append(item)            
        files = sorted(files, key=lambda x: x['time'], reverse=True)
        # build rss head
        img_path = os.path.join(show_web_dir,"img.jpg")
        rss_output = '<?xml version="1.0" encoding="UTF-8"?>\n' \
                    '<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">\n' \
                    '  <channel>\n' \
                    f'    <title>{channel}</title>\n' \
                    f'    <itunes:image href="{img_path}" />'
        # build rss body from files list
        for item in files:
            url = os.path.join(show_web_dir,urllib.parse.quote(item['fname']))
            if item['fname'].endswith('.mp3'):
                pub_date = time.strftime('%a, %d %b %Y %H:%M:%S %z', time.localtime(item['time']))
                rss_output += f"""\n    <item>
                <title>{saxutils.escape(fetch_file_by_id(cursor,item["name"]))}</title>
                <enclosure url="{saxutils.escape(url)}" length="{item["length"]}" type="audio/mpeg" />
                <guid isPermaLink="true">{saxutils.escape(url)}</guid>
                <pubDate>{pub_date}</pubDate>\n    </item>"""
            elif item['fname'].endswith('.m4a'):
                pub_date = time.strftime('%a, %d %b %Y %H:%M:%S %z', time.localtime(item['time']))
                rss_output += f"""\n    <item>
                <title>{saxutils.escape(fetch_file_by_id(cursor,item["name"]))}</title>
                <enclosure url="{saxutils.escape(url)}" length="{item["length"]}" type="audio/mp4" />
                <guid isPermaLink="true">{saxutils.escape(url)}</guid>
                <pubDate>{pub_date}</pubDate>\n    </item>"""
            else :
                pass
        # build rss foot
        rss_output += '\n  </channel>\n' \
                    '</rss>'
        # write rss index file
        with open(
            os.path.join(data_dir, channel, "index.rss"),"w",encoding="utf-8"
            ) as index_file:
            index_file.write(rss_output)
        # update new podcast items list
        update_list= []
        try:
            with open(
                os.path.join(data_dir, audio_files_dir, "archive_list"),"r"
                ) as archive_list_file:
                archive_list = archive_list_file.read().split("\n")
        except FileNotFoundError:
                archive_list = []
        finally:
                for item in files:
                    if item["name"] not in set(archive_list):
                        update_list.append(item["name"])
                        archive_list.append(item["name"])
                        with open(
                            os.path.join(data_dir, audio_files_dir, "archive_list",),"w"
                            ) as archive_list_file:
                            for podcast_name in archive_list:
                                archive_list_file.write(podcast_name + "\n")
        full_update_list.extend(update_list)
    cursor.close()
    conn.close()
    return full_update_list
