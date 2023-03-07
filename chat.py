import random
import json
import os

from typing import List
from loguru import logger
from asyncio import sleep
from sqlitedict import SqliteDict
import openai

from hoshino import R, Service, priv
from hoshino.tool import anti_conflict
from hoshino.config import NICKNAME

from .setting import settings, Config
from .AIChat import AIChat

config_file_name = settings["config_file_name"]
group_conversation_file_name = settings["group_conversation_file_name"]
temp_chat_file_name = settings["temp_chat_file_name"]
prefix = settings["prefix"]
sleep_time = settings["sleep_time"]
DEFAULT_AI_CHANCE = settings["DEFAULT_AI_CHANCE"]
Keywords = settings["Keywords"]
BLACK_WORD = settings["BLACK_WORD"]
BANNED_WORD = settings["BANNED_WORD"]
eqa_db_dir = settings["eqa_db_dir"]
openai.api_key = settings["api_key"]

group_conversation_path = os.path.join(os.path.dirname(__file__), group_conversation_file_name)
temp_chat_path = os.path.join(os.path.dirname(__file__), temp_chat_file_name)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), config_file_name)

help_text = """全部指令：
群AI会随机冒出来水群，也会在你提到她，回复她，艾特她的时候回复你
0. @bot+闭嘴：禁用群AI(临时会话不会受影响)
1. 调整AI概率+{0-50之间的整数}: 调整群AI随机触发的概率
2. 当前AI概率：查看群AI随机触发的概率
3. 清空群设定：清空群AI保存的所有人格设定和对话
4. 清空群对话：清空群AI保存的所有对话
5. 查看本群token：当前群AI消耗的token，清空群对话会将token清零
6. 添加群设定+{输入你的调教指令}：给群AI添加调教指令
7. 创建临时会话：创建一个不受群设定影响的临时chatGPT会话，创建后chatGPT会回复你在群里的所有消息，一分钟内没收到消息会自动结束
8. 继续临时会话：继续你上次的临时chatGPT会话
9. 结束临时会话：提前结束你的临时chatGPT会话
10. /t + 内容：用前缀"/t"触发群AI，可在setting.py里修改前缀
"""

#get your bot's nickname from __bot__.py
NICKNAME_list = []
if type(NICKNAME) == str:
    if NICKNAME == "":
        NICKNAME = "星乃"
    NICKNAME_list.append(NICKNAME)
else:
    NICKNAME_list = list(NICKNAME)
Keywords.extend(NICKNAME_list)

ai_chance = Config(CONFIG_PATH)

sv = Service(
    name="群AI&chatGPT",  # 功能名
    visible=True,  # 可见性
    enable_on_default=True,  # 默认启用
    bundle="娱乐",  # 分组归类
    help_=help_text,  # 帮助说明

)

conversation_list = {} #TODO: change variable name to conversation_dict
temp_chats = {}
# init conversation_list
with open(group_conversation_path) as file:
    group_conversations = json.load(file)

for conversation_id, conversation in group_conversations.items():
    chat = AIChat()
    chat.load_dict(conversation)
    conversation_list[conversation_id] = chat

#TODO: change the attributes of each AIChat
def save_chat(group_id, chat_dict):
    group_conversations[group_id] = chat_dict
    with open(group_conversation_path, "w") as file:
        json.dump(group_conversations, file, indent=4)

def save_temp_chat(conversation_id, chat_dict):
    with open(temp_chat_path) as file:
        temp_chat_record = json.load(file)
    temp_chat_record[conversation_id] = chat_dict
    with open(temp_chat_path, "w") as file:
        json.dump(temp_chat_record, file, indent=4)

def init_db(db_dir, tablename=''):
    #从EQA.util偷来的function
    return SqliteDict(db_dir,
                      tablename=tablename,
                      encode=json.dumps,
                      decode=json.loads,
                      autocommit=True)

if eqa_db_dir:
    #如果settings填了eqa_db_dir,那么获取数据
    db = init_db(eqa_db_dir, tablename='unnamed')
    reg_db = init_db(eqa_db_dir, tablename='reg')
    
def get_eqa_question_list(group_id):
    # 获取本群EQA设定的问题库
    db_list = []
    if eqa_db_dir:
        db_list = list(db.values()) + list(reg_db.values())
    # 获取当前群设置的问题列表
    db_list = list(filter(lambda x: (x[0]['group_id'] if isinstance(x, list) else x['group_id']) == group_id, db_list))
    qns_list = []
    for i in db_list:
        qns_list.append(i[0]['qus'])
    return qns_list

@sv.on_fullmatch('闭嘴', only_to_me=True)
async def shut_up(bot, ev):
    group_id = str(ev.group_id)
    if group_id in conversation_list:
        del conversation_list[group_id]
        ai_chance.set_chance(group_id, 0)
        await bot.send(ev, f'好的，如果你想我了，可以随时调整AI概率唤醒我哦.')
        return
    await bot.send(ev, f'可我没说话啊?')

@sv.on_prefix(('调整AI概率'))
async def enable_aichat(bot, ev):
    s = ev.message.extract_plain_text()
    if s:
        if s.isdigit() and 0<=int(s)<51:
            chance = int(s)
        else:
            await bot.finish(ev, '参数错误: 请输入0-50之间的整数.')
    else:
        chance = DEFAULT_AI_CHANCE     # 后面不接数字时调整为默认概率
    ai_chance.set_chance(str(ev.group_id), chance)
    group_id = str(ev.group_id)
    if group_id not in conversation_list:
        chat = AIChat()
        conversation_list[group_id] = chat
        chat_dict = chat.to_dict()
        save_chat(group_id, chat_dict)
    await bot.send(ev, f'人工智障已启用, 当前bot回复概率为{chance}%.')

@sv.on_fullmatch('当前AI概率')
async def check_aichat(bot, ev):
    try:
        chance = ai_chance.chance[str(ev.group_id)]
    except:
        chance = 0
    await bot.send(ev, f'当前bot回复概率为{chance}%.')

@sv.on_message('group')
@anti_conflict
async def ai_chat(bot, ev):
    qq = str(ev.user_id)
    group_id = str(ev.group_id)
    conversation_id = "_".join([qq, group_id])
    msg = ev['message'].extract_plain_text().strip()
    if not msg:
    #没有文字，比如只是照片
        return
    for word in BLACK_WORD:
    #防止和clanbattle以及其他原生指令冲突
        if word in msg:
            return
    if msg in get_eqa_question_list(group_id):
    #防止和EQA冲突
        return
    if conversation_id in temp_chats:
    # 进行临时会话
        temp_chats[conversation_id] = True
        chat = conversation_list[conversation_id]
        reply = chat.get_reply(msg)
        await bot.send(ev, reply)
        sv.logger.info(
            f"问题：{msg} ---- 回答：{reply}"
        )
        return
    # 接下来进行群对话
    if group_id not in ai_chance.chance:
        return
    text = str(ev['message'])
    contains_keyword = False
    if f'[CQ:at,qq={ev["self_id"]}]' in text:
    #如果被艾特，则必定触发
        contains_keyword = True
    for words in Keywords:
    #如果被提到了关键字，则必定触发
        if words in msg:
            contains_keyword = True
    if not contains_keyword and not random.randint(1,100) <= int(ai_chance.chance[str(ev.group_id)]):
    #roll触发概率
        return
    if group_id not in conversation_list:
        return
    chat = conversation_list[group_id]
    reply = chat.get_reply(msg)
    await bot.send(ev, reply)
    sv.logger.info(
        f"问题：{msg} ---- 回答：{reply}"
    )
    chat_dict = chat.to_dict()
    save_chat(group_id, chat_dict)

@sv.on_prefix(prefix)
async def prefix_chat(bot, ev):
    group_id = str(ev.group_id)
    msg = ev.message.extract_plain_text()
    if group_id not in conversation_list:
        await bot.send(ev, "本群没开启群聊天功能,请先使用指令”调整AI概率+零到五十之间任意数字“初始化群聊天功能")
        return
    chat = conversation_list[group_id]
    reply = chat.get_reply(msg)
    await bot.send(ev, reply)
    sv.logger.info(
        f"问题：{msg} ---- 回答：{reply}"
    )
    chat_dict = chat.to_dict()
    save_chat(group_id, chat_dict)

@sv.on_fullmatch("清空群设定")
async def clear_group_all(bot, ev):
    qq = str(ev.user_id) #TODO: check priv
    group_id = str(ev.group_id)
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.send(ev, "您的权限不足")
        return
    if group_id not in conversation_list:
        await bot.send(ev, "本群没开启群聊天功能,请先使用指令”调整AI概率+零到五十之间任意数字“初始化群聊天功能")
        return
    chat = conversation_list[group_id]
    chat.clear_all()
    chat_dict = chat.to_dict()
    save_chat(group_id, chat_dict)
    await bot.send(ev, "已清空群对话和设定")

@sv.on_fullmatch("清空群对话")
async def clear_group_conversation(bot, ev):
    qq = str(ev.user_id) #TODO: check priv
    group_id = str(ev.group_id)
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.send(ev, "您的权限不足")
        return
    if group_id not in conversation_list:
        await bot.send(ev, "本群没开启群聊天功能,请先使用指令”调整AI概率+零到五十之间任意数字“初始化群聊天功能")
        return
    chat = conversation_list[group_id]
    chat.clear_messages()
    chat_dict = chat.to_dict()
    save_chat(group_id, chat_dict)
    await bot.send(ev, "已清空群对话")

@sv.on_fullmatch("查看本群token")
async def clear_group_conversation(bot, ev):
    qq = str(ev.user_id) #TODO: check priv
    group_id = str(ev.group_id)
    if group_id not in conversation_list:
        await bot.send(ev, "本群没开启群聊天功能,请先使用指令”调整AI概率+零到五十之间任意数字“初始化群聊天功能")
        return
    chat = conversation_list[group_id]
    token_cost = chat.get_full_token_cost()
    await bot.send(ev, f"本群群聊天功能共使用{chat.get_full_token_cost()}枚token.")

@sv.on_prefix("添加群设定")
async def add_setting(bot, ev):
    new_setting = ev.message.extract_plain_text()
    qq = str(ev.user_id)
    group_id = str(ev.group_id)
    if group_id not in conversation_list:
        await bot.send(ev, "本群没开启群聊天功能,请先使用指令”调整AI概率+零到五十之间任意数字“初始化群聊天功能")
        return
    chat = conversation_list[group_id]
    chat.add_conversation_setting(new_setting)
    chat_dict = chat.to_dict()
    save_chat(group_id, chat_dict)
    await bot.send(ev, "已添加群设定")

@sv.on_fullmatch("继续临时会话")
async def continue_temp_chat(bot, ev):
    qq = str(ev.user_id)
    group_id = str(ev.group_id)
    conversation_id = "_".join([qq, group_id])
    if conversation_id not in conversation_list:
        chat = AIChat(
                    conversation_id = conversation_id,
                    qq = qq,
                    group_id = group_id
        )
        with open(temp_chat_path) as file:
            temp_chat_record = json.load(file)
        if conversation_id in temp_chat_record:
            chat.load_dict(temp_chat_record[conversation_id])
            await bot.send(ev, f"已加载上次的临时聊天记录，上次临时聊天共使用{chat.get_full_token_cost()}枚token.")
        else:
            await bot.send(ev, "未找到上次的临时聊天记录，已创建新纪录.")
        conversation_list[conversation_id] = chat
    temp_chats[conversation_id] = False
    await sleep(sleep_time)
    while conversation_id in temp_chats:
        if temp_chats[conversation_id] == False:
            break
        else:
            temp_chats[qq] = False
            await sleep(sleep_time)
    if conversation_id in temp_chats:
        del temp_chats[conversation_id]
        await bot.send(ev, f"会话结束,合计使用{chat.get_full_token_cost()}枚token.")
    chat_dict = chat.to_dict()
    save_temp_chat(conversation_id, chat_dict)

@sv.on_fullmatch("创建临时会话")
async def start_temp_chat(bot, ev):
    qq = str(ev.user_id)
    group_id = str(ev.group_id)
    conversation_id = "_".join([qq, group_id])
    if conversation_id in temp_chats:
        await bot.send(ev, "不能重复创建临时会话，请先使用指令“结束临时会话”.")
    chat = AIChat(
                conversation_id = conversation_id,
                qq = qq,
                group_id = group_id
    )
    conversation_list[conversation_id] = chat
    temp_chats[conversation_id] = False
    await bot.send(ev, "已创建临时会话，你好！有什么我可以帮助你的吗？")
    await sleep(sleep_time)
    while conversation_id in temp_chats:
        if temp_chats[conversation_id] == False:
            break
        else:
            temp_chats[conversation_id] = False
            await sleep(sleep_time)
    if conversation_id in temp_chats:
        del temp_chats[conversation_id]
        await bot.send(ev, f"临时会话结束,合计使用{chat.get_full_token_cost()}枚token.")
    chat_dict = chat.to_dict()
    save_temp_chat(conversation_id, chat_dict)

@sv.on_fullmatch(('结束临时会话'))
async def end_temp_chat(bot, ev):
    qq = str(ev.user_id)
    group_id = str(ev.group_id)
    conversation_id = "_".join([qq, group_id])
    if conversation_id in temp_chats:
        del temp_chats[conversation_id]
        chat = conversation_list[conversation_id]
        await bot.send(ev, f"临时会话结束,合计使用{chat.get_full_token_cost()}枚token.")
        chat_dict = chat.to_dict()
        save_temp_chat(conversation_id, chat_dict)
    else:
        await bot.send(ev, "错误404，未找到临时会话")
    return
