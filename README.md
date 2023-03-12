# 群AI&chatGPT临时会话 二合一
星乃Hoshino插件，使用openai的GPT3.5来让你的bot活起来，同时还能正常使用chatGPT的功能。

加了一个反并发，这个需要[反并发插件](https://github.com/lhhxxxxx/hoshino_tool)

还加了一个反[eqa](https://github.com/pcrbot/erinilis-modules/tree/master/eqa)的并发，如果没装eqa就在`setting.py`里把`eqa_db_dir`那行改为`"eqa_db_dir" = "",`

## 全部指令：
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

## 安装指南：

安装依赖`pip install openai`

安装依赖`pip install sqlitedict`

安装依赖`pip install collections`

在`hoshino/modules/`的目录中克隆本插件`git clone https://github.com/joeyHXD/aichat_chatGPT_API.git`

在`hoshino`的目录中加入[反并发`tool.py`](https://github.com/lhhxxxxx/hoshino_tool),注意是在hoshino目录下面，不是modules,如果反并发报错说明你的星乃该更新了

去 [openai官网]`https://platform.openai.com/account/api-keys` 获取API key

在`setting.py`的`api_key`填写API key,以及修改一些设定

在 `HoshinoBot\hoshino\config\__bot__.py` 文件的 `MODULES_ON` 加入 `aichat_chatGPT_API`，反并发不需要改`__bot__.py`

然后重启 HoshinoBot，并在想要使用的QQ群里输入指令 `启用 群AI&chatGPT`和`调整AI概率 10`

如果没问题的话应该就是能用了，如果想调整chatGPT的模型设定可以去AIChat的__init__里改，比如说更换模型，或者增加回复的字数上限

有什么不清楚的地方可以发送`帮助群AI&chatGPT`

建议经常清空一次群对话，防止token使用速度越来越快

临时会话的示范图：![image](https://user-images.githubusercontent.com/68325229/222948188-5dab4051-d422-495a-a2f2-ba9ef2eb8c9b.png)

