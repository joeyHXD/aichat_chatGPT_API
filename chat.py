import random
import json
import os
import re

from typing import List
from asyncio import sleep, get_event_loop
from concurrent.futures import ThreadPoolExecutor
from sqlitedict import SqliteDict
import openai

from hoshino import R, Service, priv
from hoshino.tool import anti_conflict
from hoshino.config import NICKNAME
from hoshino.typing import MessageSegment
from .setting import Config
from .AIChat import AIChat
from .text2img import image_draw

# 获取初始设定
cf = Config()
Keywords = cf.Keywords
openai.api_key = cf.api_key
openai.proxy = cf.proxy
model_used = cf.model_used # 无效参数
if cf.voice:
    import deepl
    from .get_voice import voiceApi, getvoice
    translator = deepl.Translator(cf.deepL_api)

group_conversation_path = os.path.join(os.path.dirname(__file__), cf.group_conversation_file_name)
temp_chat_path = os.path.join(os.path.dirname(__file__), cf.temp_chat_file_name)

#get your bot's nickname from __bot__.py
NICKNAME_list = []
if type(NICKNAME) == str:
    if NICKNAME == "":
        NICKNAME = "星乃"
    NICKNAME_list.append(NICKNAME)
else:
    NICKNAME_list = list(NICKNAME)
Keywords.extend(NICKNAME_list)

executor = ThreadPoolExecutor()

sv = Service(
    name="群AI&chatGPT",  # 功能名
    visible=True,  # 可见性
    enable_on_default=True,  # 默认启用
    bundle="娱乐",  # 分组归类
    help_=cf.help_text,  # 帮助说明
)

conversation_list = {} #TODO: change variable name to conversation_dict
temp_chats = {}
qq_to_username = {}
regex = re.compile(r'\[CQ:at,qq=(\d+)\]')
# init conversation_list
with open(group_conversation_path, encoding="utf-8") as file:
    group_conversations = json.load(file)

for conversation_id, conversation in group_conversations.items():
    chat = AIChat(bot_name=NICKNAME_list[0])
    chat.load_dict(conversation)
    conversation_list[conversation_id] = chat

#TODO: change the attributes of each AIChat
def save_chat(group_id, chat_dict):
    group_conversations[group_id] = chat_dict
    with open(group_conversation_path, "w", encoding="utf-8") as file:
        json.dump(group_conversations, file, indent=4, ensure_ascii=False)

def save_temp_chat(conversation_id, chat_dict):
    with open(temp_chat_path, encoding="utf-8") as file:
        temp_chat_record = json.load(file)
    temp_chat_record[conversation_id] = chat_dict
    with open(temp_chat_path, "w", encoding="utf-8") as file:
        json.dump(temp_chat_record, file, indent=4, ensure_ascii=False)

def init_db(db_dir, tablename=''):
    #从EQA.util偷来的function
    return SqliteDict(db_dir,
                      tablename=tablename,
                      encode=json.dumps,
                      decode=json.loads,
                      autocommit=True)

if cf.eqa_db_dir:
    #如果settings填了eqa_db_dir,那么获取数据
    db = init_db(cf.eqa_db_dir, tablename='unnamed')
    reg_db = init_db(cf.eqa_db_dir, tablename='reg')
    
def get_eqa_question_list(group_id):
    # 获取本群EQA设定的问题库
    db_list = []
    if cf.eqa_db_dir:
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
        cf.set_chance(group_id, 0)
        await bot.send(ev, f'好的，如果你想{NICKNAME_list[0]}了，可以随时调整AI概率唤醒我哦.')
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
    cf.set_chance(str(ev.group_id), chance)
    group_id = str(ev.group_id)
    if group_id not in conversation_list:
        chat = AIChat(
            bot_name = NICKNAME_list[0],
            group_id = group_id,
            model = cf.model_used,
            max_tokens = cf.ai_chat_max_token,
            group_context_max = cf.group_context_max
        )
        conversation_list[group_id] = chat
        chat_dict = chat.to_dict()
        save_chat(group_id, chat_dict)
    await bot.send(ev, f'{NICKNAME_list[0]}已启用, 当前{NICKNAME_list[0]}回复概率为{chance}%.')

@sv.on_fullmatch('当前AI概率')
async def check_aichat(bot, ev):
    try:
        chance = cf.chance[str(ev.group_id)]
    except:
        chance = 0
    await bot.send(ev, f'当前{NICKNAME_list[0]}回复概率为{chance}%.')

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
    for word in cf.BLACK_WORD:
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
        loop = get_event_loop()
        reply = await loop.run_in_executor(executor, chat.get_reply, msg)
        # reply = chat.get_reply(msg)
        sv.logger.info(
            f"问题：{msg} ---- 回答：{reply}"
        )
        if len(reply) > cf.max_len_image_draw:
            pic = image_draw(reply)
            await bot.send(ev, f'[CQ:image,file={pic}]')
        else:
            await bot.send(ev, reply)
        return
    # 接下来进行群对话
    if group_id not in cf.chance:
    #未启动
        return
    if group_id not in conversation_list:
    #未启动或者被闭嘴了
        return
    chat = conversation_list[group_id]
    contains_keyword = False
    for prefix in cf.prefixes:
    # 检查前缀，text会包含CQ码，所以用msg，不是bug
        if msg.startswith(prefix):
            contains_keyword = True
    text = str(ev['message'])
    qq_numbers = regex.findall(text)
    # 检查所有被艾特的QQ号
    qq_numbers.append(qq)
    if group_id not in qq_to_username:
        qq_to_username[group_id] = {}
    for qq_number in qq_numbers:
        if qq_number not in qq_to_username[group_id]:
        # 获取群昵称
            info = await bot.get_group_member_info(
                        group_id=int(group_id), user_id=int(qq_number)
                    )
            username = info.get("card", "") or info.get("nickname", "")
            qq_to_username[group_id][qq_number] = username
    if cf.group_context_max != 0:
    # 输入群消息，即使不回复也会先输入，帮助以后的回复
        username = qq_to_username[group_id][qq]
        msg = regex.sub(lambda m: '@' + qq_to_username[group_id].get(m.group(1), m.group(1)), text)
        msg = re.sub(r'\[CQ:[^]]+\]', '', msg)
        msg = f"{username}：{msg}"
        chat.add_group_context("user", msg)
    if str(ev["self_id"]) in qq_numbers:
    #如果被艾特，则必定触发
        contains_keyword = True
    for words in Keywords:
    #如果被提到了关键字，则必定触发
        if words in msg:
            contains_keyword = True
    if not contains_keyword and not random.randint(1,100) <= int(cf.chance[str(group_id)]):
    #roll触发概率
        return
    loop = get_event_loop()
    reply = await loop.run_in_executor(executor, chat.get_group_reply, msg)
    # 去掉前缀 "bot_name:"
    split_symbols = [':', '：']
    for symbol in split_symbols:
        split_reply = reply.split(symbol)
        if len(split_reply) > 1:
            reply = symbol.join(split_reply[1:])
            break
    sv.logger.info(
        f"问题：{msg} ---- 回答：{reply}"
    )
    if len(reply) > cf.max_len_image_draw:
        pic = image_draw(reply)
        await bot.send(ev, f'[CQ:image,file={pic}]')
    else:
        await bot.send(ev, reply)
    chat_dict = chat.to_dict()
    save_chat(group_id, chat_dict)
    if cf.voice:
    # 使用DeepL翻译成日文
    # 使用MoeTTS的ATRI语音API，最大只能读50字
        text = translator.translate_text(reply, target_lang="JA").text
        character = "ATRI"
        if len(text) > 50:
            text = text.split("。")[0]
        if len(text) > 50:
            text = text[:50]
        sv.logger.info(f"翻译：{text}")
        A = getvoice("ATRI",29)
        voice = await A.gethash(text)
        final_voice = MessageSegment.record(voice)
        await bot.send(ev, final_voice)
    
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
    if conversation_id in temp_chats:
        await bot.send(ev, "不能重复创建临时会话，请先使用指令“结束临时会话”.")
        return
    if conversation_id not in conversation_list:
        chat = AIChat(
                    bot_name = NICKNAME_list[0],
                    conversation_id = conversation_id,
                    qq = qq,
                    group_id = group_id,
                    model = cf.model_used,
                    max_tokens = cf.temp_chat_max_token,
                    group_context_max = cf.group_context_max

        )
        with open(temp_chat_path) as file:
            temp_chat_record = json.load(file)
        if conversation_id in temp_chat_record:
            chat.load_dict(temp_chat_record[conversation_id])
            await bot.send(ev, f"已加载上次的临时聊天记录，上次临时聊天共使用{chat.get_full_token_cost()}枚token.")
        else:
            await bot.send(ev, "未找到上次的临时聊天记录，已创建新纪录.")
        conversation_list[conversation_id] = chat
    else:
        await bot.send(ev, f"已加载上次的临时聊天记录，上次临时聊天共使用{conversation_list[conversation_id].get_full_token_cost()}枚token.")
    temp_chats[conversation_id] = False
    await sleep(cf.sleep_time)
    while conversation_id in temp_chats:
        if temp_chats[conversation_id] == False:
            break
        else:
            temp_chats[conversation_id] = False
            await sleep(cf.sleep_time)
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
        return
    chat = AIChat(
                bot_name = NICKNAME_list[0],
                conversation_id = conversation_id,
                qq = qq,
                group_id = group_id,
                model = cf.model_used,
                max_tokens = cf.temp_chat_max_token,
                group_context_max = cf.group_context_max
    )
    conversation_list[conversation_id] = chat
    temp_chats[conversation_id] = False
    await bot.send(ev, "已创建临时会话，你好！有什么我可以帮助你的吗？")
    await sleep(cf.sleep_time)
    while conversation_id in temp_chats:
        if temp_chats[conversation_id] == False:
            break
        else:
            temp_chats[conversation_id] = False
            await sleep(cf.sleep_time)
    if conversation_id in temp_chats:
        del temp_chats[conversation_id]
        await bot.send(ev, f"临时会话结束,合计使用{chat.get_full_token_cost()}枚token.")
    chat_dict = chat.to_dict()
    save_temp_chat(conversation_id, chat_dict)

@sv.on_fullmatch('结束临时会话')
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

@sv.on_fullmatch('查看群设定')
async def check_settings(bot, ev):
    qq = str(ev.user_id)
    group_id = str(ev.group_id)
    if group_id not in conversation_list:
        await bot.send(ev, "本群没开启群聊天功能,请先使用指令”调整AI概率+零到五十之间任意数字“初始化群聊天功能")
        return
    chat = conversation_list[group_id]
    settings = chat.get_system_inputs()
    reply = "\n".join(settings)
    await bot.send(ev, reply)

@sv.on_prefix("调整上限")
async def change_max_token(bot, ev):
    s = ev.message.extract_plain_text()
    qq = str(ev.user_id)
    group_id = str(ev.group_id)
    if group_id not in conversation_list:
        await bot.send(ev, "本群没开启群聊天功能,请先使用指令”调整AI概率+零到五十之间任意数字“初始化群聊天功能")
        return
    max_token = cf.ai_chat_max_token # 后面不接数字时调整为默认概率
    if s:
        if s.isdigit() and 0<=int(s)<4000:
            max_token = int(s)
        else:
            await bot.finish(ev, '参数错误: 请输入0-4000之间的整数.')
            return
    chat = conversation_list[group_id]
    chat.max_tokens = max_token
    chat_dict = chat.to_dict()
    save_chat(group_id, chat_dict)
    await bot.send(ev, f"已修改成{max_token}tokens")

@sv.on_prefix("调整记忆")
async def change_group_context_max(bot, ev):
    s = ev.message.extract_plain_text()
    qq = str(ev.user_id)
    group_id = str(ev.group_id)
    if group_id not in conversation_list:
        await bot.send(ev, "本群没开启群聊天功能,请先使用指令”调整AI概率+零到五十之间任意数字“初始化群聊天功能")
        return
    group_context_max = cf.group_context_max # 后面不接数字时调整为默认概率
    if s:
        if s.isdigit() and -1<=int(s)<100:
            group_context_max = int(s)
        else:
            await bot.finish(ev, '参数错误: 请输入-1到100之间的整数.')
            return
    chat = conversation_list[group_id]
    chat.group_context_max = group_context_max
    chat_dict = chat.to_dict()
    save_chat(group_id, chat_dict)
    await bot.send(ev, f"塑料记忆已修改成{group_context_max}。请注意bot能处理的token数是有上限的，她不能陪伴你一身。")

@sv.on_fullmatch('看看内裤') # 查看所有信息
async def check_settings(bot, ev):
    qq = str(ev.user_id)
    group_id = str(ev.group_id)
    if group_id not in conversation_list:
        await bot.send(ev, "本群没开启群聊天功能,请先使用指令”调整AI概率+零到五十之间任意数字“初始化群聊天功能")
        return
    chat = conversation_list[group_id]
    reply = json.dumps(chat.to_dict(), indent=2, ensure_ascii=False)
    pic = image_draw(reply)
    await bot.send(ev, f'[CQ:image,file={pic}]')