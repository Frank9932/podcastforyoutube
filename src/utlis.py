import os
import re
import json
import time
import urllib.parse
import xml.sax.saxutils as saxutils
from requests import post


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

def remove_temp_files(dir):
    try:
        for root, dirs, files in os.walk(dir):
            for file in files:
                file_path = os.path.join(root, file)
                os.remove(file_path)
    finally:
        pass

def create_rss_file(channels, metadata_list, temp_dir, web_dir):
    valid_episodes =[]
    for channel in channels.keys():
        episodes = []
        for metadata in metadata_list:
            # archive_id, 
            # channel, 
            # yt_channel, 
            # utime, 
            # ctime, 
            # file_size, 5
            # file_title, 
            # text_content
            if channels[channel]["keep_old"]:
                seconds_7_days_ago = 0
            else:
                # seconds_7_days_ago = time.time() - (7 * 24 * 3600) # filter files 7 days
                seconds_7_days_ago = time.time() - (60) # test
            if metadata[1] == channel and metadata[4] > seconds_7_days_ago :
                episodes.append(metadata)
        if not episodes :
            continue
        episodes = sorted(episodes, key=lambda x: x[4], reverse=True)

        # build rss head
        img_path = os.path.join(web_dir,f"img_{channel}.jpg")
        rss_output = '<?xml version="1.0" encoding="UTF-8"?>\n' \
                    '<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">\n' \
                    '  <channel>\n' \
                    f'    <title>{channel}</title>\n' \
                    f'    <itunes:image href="{img_path}" />'
        
        # build rss body from episodes list
        for episode in episodes:
            url = f'{web_dir}{urllib.parse.quote(episode[0])}.m4a'
            pub_date = time.strftime('%a, %d %b %Y %H:%M:%S %z', time.localtime(episode[4]))
            title = saxutils.escape(episode[6])
            text_content = episode[7]
            rss_output += f"""\n    <item>
            <title>{title}</title>
            <enclosure url="{url}" length="{episode[5]}" type="audio/mp4" />
            <guid isPermaLink="true">{url}</guid>
            <pubDate>{pub_date}</pubDate>
            <description><![CDATA[{text_content}]]></description>\n    </item>"""

        # build rss foot
        rss_output += '\n  </channel>\n' \
                    '</rss>'
        # write rss index file
        with open(
            os.path.join(temp_dir, f"index_{channel}.rss"),"w",encoding="utf-8"
            ) as index_file:
            index_file.write(rss_output)
        
        valid_episodes.extend(episodes)
    return valid_episodes

def process_subtitle(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as file:
        _text = file.read()
    lines = _text.splitlines()
    text_lines = []
    for line in lines:
        if re.match(r'^\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}$', line):
            continue
        elif line.strip() and not line.startswith("WEBVTT") and not line.startswith("Kind:") and not line.startswith("Language:"):
            text_lines.append(line.strip())
        result = "\n".join(text_lines)
    return result