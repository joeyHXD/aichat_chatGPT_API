import os
import json

settings = {
    "config_file_name": "config.json",#文件名
    "group_conversation_file_name": "group_conversation.json",#文件名
    "temp_chat_file_name": "temp_chat.json",#文件名
    "api_key": "",#openai 的 API key, https://platform.openai.com/account/api-keys
    "prefix": "/t", #触发群AI的前缀
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
    ),# 一些不希望触发的关键字
    "eqa_db_dir": "./hoshino/modules/eqa/data/db.sqlite"# eqa的数据库位置
}

class Config:
    chance = {}
    config = {}
    def __init__(self, config_path):
        self.config_path = config_path
        self.load_config()

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