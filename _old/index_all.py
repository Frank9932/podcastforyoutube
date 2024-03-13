import os
import time

# 重命名文件名中的特殊字符
def RenameFile(files_dir):
    for filename in os.listdir(files_dir):
        if filename.endswith(".mp3"):
            # new_filename = filename.replace("[", "【")
            # new_filename = new_filename.replace("]", "】")
            new_filename = filename.replace("&", "_")
            new_filename = new_filename.replace("#", "-")
            os.rename(os.path.join(files_dir, filename),
            os.path.join(files_dir, new_filename))
           

# make rss file 
def create_rss_file(podcast_class, rss_web_location):

    files_dir =     local_podcast_location = + podcast_class
    title = podcast_class
    location = rss_web_location
    files = []
    archive_list = []
    # 重命名文件名中的特殊字符
    RenameFile(files_dir)
    # 遍历指定目录下的所有文件
    for filename in os.listdir(files_dir):
            filepath = os.path.join(files_dir, filename)
            # 判断是否为文件以及文件扩展名是否为.mp3、.m4a或.aac
            if os.path.isfile(filepath) and filename.lower().endswith(('.mp3', '.m4a', '.aac')):
                name = os.path.splitext(filename)[0]
                item = {
                    'path': filepath,                   # 文件路径
                    'name': name,                       # 文件名（不带扩展名）
                    'fname': filename,                  # 带扩展名的文件名
                    'time': os.path.getctime(filepath),  # 创建时间
                    'length': os.path.getsize(filepath)  # 文件大小
                }
                files.append(item)
        
        # 按照文件创建时间对文件进行排序
    files = sorted(files, key=lambda x: x['time'])

        # 构造RSS输出字符串
    rss_output = '<?xml version="1.0" encoding="utf-8"?>\n' \
                    '<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">\n' \
                    '  <channel>\n' \
                    f'    <title>{title}</title>\n' \
                    f'    <itunes:image href="{location}img.jpg" />\n'
        
    # 遍历文件列表，生成每个文件的RSS项
    for item in files:
        url = location + item['fname']        
        # 根据文件扩展名确定媒体类型
        if item['fname'].endswith('.mp3'):
            mime = 'audio/mp3'
        elif item['fname'].endswith('.webm'):
            mime = 'audio/webm'
        else:
            mime = 'audio/mp4'
    
        # 将创建时间转换为指定格式的时间字符串
        pub_date = time.strftime('%a, %d %b %Y %H:%M:%S %z', time.localtime(item['time']))
        
        # 构造每个文件的RSS项
        rss_output += f'    <item>\n' \
                f'      <title>{item["name"]}</title>\n' \
                f'      <enclosure url="{url}"\n' \
                f'                 length="{item["length"]}"\n' \
                f'                 type="{mime}" />\n' \
                f'      <guid isPermaLink="true">{url}</guid>\n' \
                f'      <pubDate>{pub_date}</pubDate>\n' \
                f'    </item>\n'
    
        rss_output += '  </channel>\n' \
                '</rss>'
                
                
    # 创建RSS index文件
    location_by_class = rss_web_location + podcast_class +"/"
    with open(files_dir+"/index.rss", "w") as index_file:
         index_file.write(rss_output)        

    #更新通知列表
    try:
        with open(files_dir+"/archive_list","r") as file:
            archive_list = file.read().split("\n")
    except :
            archive_list = []
    finally:
            update_list= []
            for item in files:
                if item["name"] not in set(archive_list):
                    update_list.append(item["name"])
                    archive_list.append(item["name"])
                    with open(files_dir+"/archive_list","w") as file:
                        for file_name in archive_list:
                            file.write(file_name + "\n")
            return update_list
            
def index_all(config_dic,rss_web_location):
    full_update_list = []
    for item in config_dic.keys():
        class_name =   item        
        small_list = create_rss_file(class_name,rss_web_location)
        full_update_list.extend(small_list)
    return full_update_list    
        
if __name__ == "__main__":
    podcast_class = "AINews"
    rss_web_location = "https://blog.7423456.xyz/podcast/youtube_channels/"
    print(len(create_rss_file(podcast_class,rss_web_location)))