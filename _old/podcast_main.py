from  index_all import *
from  download_media import *
import asyncio
from  user_data import *
from  sendTgMessage import *



#download
download_media(config_dic)

#make index
new_update = index_all(config_dic,rss_web_location)
#print(new_update)

if not len(new_update) == 0 :
       sendTgMessage("\n❗❗❗❗❗❗\n\n".join(new_update),bot_token,group_list[1])