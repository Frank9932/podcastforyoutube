import asyncio
from telegram import Bot
from user_data import bot_token,group_list


def sendTgMessage(msg,bot_token,group_id):
        async def send_message():
            # 创建 Bot 实例
            bot = Bot(token=bot_token)

            # 发送消息到群组
            await bot.send_message(chat_id=group_id, text=msg)

        # 创建事件循环并运行异步函数
        loop = asyncio.get_event_loop()
        loop.run_until_complete(send_message())
        loop.close()












































# from telegram import Bot
# import requests
# from bs4 import BeautifulSoup


# url = 'https://nexushub.co/wow-classic/items/arugal-alliance/Tin-ore'
# response = requests.get(url)
# html_content = response.content

# soup = BeautifulSoup(html_content, 'html.parser')
# price_element = soup.find('span', {'class': 'data-price'})
# price = price_element.text

# TEXT = "锡矿石价格是" + price

# async def send_message():
#     # 创建 Bot 实例
#     bot = Bot(token=bot_token)

#     # 发送消息到群组
#     await bot.send_message(chat_id=group_name, text=TEXT)

# # 创建事件循环并运行异步函数
# import asyncio
# loop = asyncio.get_event_loop()
# loop.run_until_complete(send_message())
# loop.close()
