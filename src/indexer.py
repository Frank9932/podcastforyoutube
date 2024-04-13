import json
import datetime
import os
import time
import html

def rename_file_by_dir(dir):
    for filename in os.listdir(dir):
        if filename.endswith(".mp3"):
            new_filename = filename.replace(" ", "-")
            new_filename = new_filename.replace("#", "-")
            os.rename(
                os.path.join(dir, filename),
                os.path.join(dir, new_filename)
                )

def create_rss_file(data_dir,show_name, web_dir):
    files = []

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
                 f'    <itunes:image href="{os.path.join(html.escape(show_web_dir), "img.jpg")}" />\n'
    
    for item in files:
        url = os.path.join(show_web_dir, item['fname'])
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

if __name__ == "__main__":
    show_name = "audiobooks"
    data_dir = "/var/www/podcast"
    web_dir = "https://learn.7423456.xyz/podcast"
    create_rss_file(show_name, data_dir, web_dir)