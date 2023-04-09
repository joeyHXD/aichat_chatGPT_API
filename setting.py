import os
import json

class Config:
    #这里是初始设置，你也可以去
    settings = {
        "config_path": "config.json",# AI概率文件名
        "group_conversation_file_name": "group_conversation.json",# 群AI文件名
        "temp_chat_file_name": "temp_chat.json",# 临时会话文件名
        "voice": False, # 是否开启语音
        "deepL_api": "", # deepL 的API key, 如果要语音功能才需要
        "api_key": "", # openai 的 API key, https://platform.openai.com/account/api-keys
        "prefixes": ["/t"], # 触发群AI的前缀,如果不要前缀就改成[],改成[""]会让bot每句话都触发
        "group_context_max": 5, # 设置为-1则无限记录群聊，0则不记录，3则记录触发群AI前的最后3条消息，让群AI更加合群
        "ai_chat_max_token": 200, # 单条群AI回复内容的最大token数，大约100汉字的感觉
        "temp_chat_max_token": 500, # 单条临时会话回复内容的最大token数，注意单次请求必须小于4096token，这包括回复内容和所有的聊天信息，如果超出可能openAPI会报错，我不确定
        "max_len_image_draw": 100, # 超出100字就会转换成图片,不想换图片就改成个3000字
        "proxy": None, # 代理格式：{"http": your_proxy, "https": your_proxy}
        "model_used": "gpt-3.5-turbo-0301", # 无效参数，暂时默认gpt-3.5-turbo，以后有空再补上
        "sleep_time": 60, #默认60秒，临时会话自动结束
        "DEFAULT_AI_CHANCE": 0, #群AI的默认概率
        "Keywords": ['bot','BOT','Bot','机器人','人工智障'], #你家bot说话的关键词，也可以把bot名字写这
        "BLACK_WORD": [
            '报刀','状态','删刀','撤销','启用','禁用','预约','催刀','尾刀','建会',
            '查看公会','入会','查看成员', '成员查看', '查询成员', '成员查询','退会',
            '清空成员','一键入会','出刀','出尾刀', '收尾','出补时刀', '补时刀', '补时',
            '掉刀','挂树','上树','锁定', '申请出刀','进度','解锁','统计','查刀','lssv',
            'disable','enable'
        ],# 一些不希望触发的关键字
        "BANNED_WORD": (
            'rbq', 'RBQ', '憨批', '废物', '死妈', '崽种', '傻逼', '傻逼玩意',
            '没用东西', '傻B', '傻b', 'SB', 'sb', '煞笔', 'cnm', '爬', 'kkp',
            'nmsl', 'D区', '口区', '我是你爹', 'nmbiss', '弱智', '给爷爬', '杂种爬','爪巴'
        ),# 无效参数，不如直接anti_abuse对吧
        "eqa_db_dir": "./hoshino/modules/eqa/data/db.sqlite",# eqa的数据库位置
        "chance": {},
        "config": {},
        "help_text": """全部指令：
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
11. 查看群设定
12. 调整上限：调整群AI每句话使用的token
13. 调整记忆：调整群AI能记住的群消息
14. 看看胖次：查看群AI的所有信息
15. 启动/禁用语音：ATRI语音
"""
    }
    def __init__(self):
        self.load_config()

    def __getattr__(self, name):
        return self.settings[name]

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as config_file:
                    self.config = json.load(config_file)
                    self.chance = self.config["ai_chance"]
            else:
                self.chance = {}
        except:
            self.chance = {}

    def save_config(self):
        self.config["ai_chance"] = self.chance
        with open(self.config_path, 'w') as config_file:
            json.dump(self.config, config_file, ensure_ascii=False, indent=4)

    def set_chance(self, gid, chance):
        self.chance[gid] = chance
        self.save_config()

    def delete_chance(self, gid):
        if gid in self.chance:
            del self.chance[gid]
            self.save_config()