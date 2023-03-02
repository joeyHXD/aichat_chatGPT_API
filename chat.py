from hoshino.tool import anti_conflict
from hoshino import Service
import os
import openai
from asyncio import sleep

sv = Service('ai')
openai.api_key = "" 
#https://platform.openai.com/account/api-keys

current_users = {}
chat_content = {}
#临时改的，暂时不分辨群号

@sv.on_message('group')
@anti_conflict
async def ai_chat(bot, ev):
    qq=str(ev.user_id)
    msg = str(ev.message.extract_plain_text()).strip()
    if not msg:
    #没有文字，比如只是照片
        return
    if qq in current_users:
        current_users[qq] = True
        messages = chat_content[qq]
        messages.append(
            {
                "role": "user", "content": msg
            }
        )
        response = openai.ChatCompletion.create(
          model="gpt-3.5-turbo",
          messages=messages
        )
        reply_message = response["choices"][0]["message"]
        chat_content[qq].append(reply_message)
        await bot.send(ev, reply_message["content"])

@sv.on_fullmatch(('chat', '聊天', '来聊天', '和我聊天'), only_to_me=True)
async def enable_aichat(bot, ev):
    qq=str(ev.user_id)
    if qq not in current_users:
        current_users[qq] = False
        chat_content[qq] = []
    await bot.send(ev, "来聊天吧")
    await sleep(60)
    while qq in current_users:
        if not current_users[qq]:
            break
        else:
            current_users[qq] = False
            await sleep(60)
    if qq in current_users:
        del current_users[qq]
        del chat_content[qq]
        await bot.send(ev, "会话结束")
    return
    
@sv.on_fullmatch(('结束会话'))
async def enable_aichat(bot, ev):
    qq=str(ev.user_id)
    if qq in current_users:
        del current_users[qq]
        del chat_content[qq]
        await bot.send(ev, "会话结束")
    else:
        await bot.send(ev, "你什么时候产生了和我会话的错觉")
    return