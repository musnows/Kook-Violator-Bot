import json
from khl import Message, PrivateMessage, Bot
from khl.card import Card, CardMessage, Element, Module, Types
# 用户数量的记录文件
from .Logging import _log
from ..file.Files import bot
from ..Gtime import get_time
from ..KookApi import upd_card, get_card_msg


async def log_msg(msg: Message) -> bool:
    """在控制台打印msg内容，用作日志
    - 检查当前频道能否执行命令
    - pm_allow: False代表私聊不允许执行并会发送信息
    - ch_allow: True则允许在任何频道执行（和config无关）

    Return
    - True: 准许执行
    - False：不给执行
    """
    try:
        # 私聊用户没有频道和服务器id
        if isinstance(msg, PrivateMessage):
            _log.info(
                f"PrivateMsg | Au:{msg.author_id} {msg.author.username}#{msg.author.identify_num} | {msg.content}")
        else:
            _log.info(
                f"G:{msg.ctx.guild.id} | C:{msg.ctx.channel.id} | Au:{msg.author_id} {msg.author.username}#{msg.author.identify_num} = {msg.content}"
            )
    except:
        _log.exception("Exception occurred")


async def api_request_failed_handler(def_name: str,
                                     excp: str,
                                     msg: Message,
                                     bot: Bot,
                                     cm=CardMessage(),
                                     send_msg: dict[str, str] = {}) -> None:
    """出现kook api异常的通用处理

    Args:
    - def_name: name of def to print in log
    - excp: taraceback.fromat_exc()
    - msg: khl.Message
    - bot: khl.Bot
    - cm: khl.card.CardMessage, for json.dumps / resend
    - send_msg: return value of msg.reply or bot.send
    """
    _log.exception(f"APIRequestFailed in {def_name} | Au:{msg.author_id}")
    err_str = f"ERR! [{get_time()}] {def_name} Au:{msg.author_id} APIRequestFailed\n{excp}"
    text = f"啊哦，出现了一些问题\n" + err_str
    text_sub = 'e'
    # 引用不存在的时候，直接向频道或者用户私聊重新发送消息
    if "引用不存在" in excp:
        if isinstance(msg, PrivateMessage):
            cur_user = await bot.client.fetch_user(msg.author_id)
            await cur_user.send(cm)
        else:
            cur_ch = await bot.client.fetch_public_channel(msg.ctx.channel.id)
            await bot.send(cur_ch, cm)
        _log.error(f"Au:{msg.author_id} | 引用不存在, 直接发送cm")
        return
    elif "json没有通过验证" in excp or "json格式不正确" in excp:
        _log.error(f"Au:{msg.author_id} | json.dumps: {json.dumps(cm)}")
        text_sub = f"卡片消息json没有通过验证或格式不正确"
    elif "屏蔽" in excp:
        _log.error(f"Au:{msg.author_id} | 用户屏蔽或权限不足")
        text_sub = f"机器人无法向您发出私信，请检查你的隐私设置"

    cm = await get_card_msg(text, text_sub)
    if send_msg:  # 非none则执行更新消息，而不是直接发送
        await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
    else:
        await msg.reply(cm)


# 基础错误的处理，带login提示(部分命令不需要这个提示)
async def base_exception_handler(def_name: str,
                                 excp: str,
                                 msg: Message,
                                 send_msg: dict[str, str] = {},
                                 debug_send=None) -> None:  # type: ignore
    """Args:
    - def_name: name of def to print in log
    - excp: taraceback.fromat_exc()
    - msg: khl.Message
    - send_msg: return value of msg.reply or bot.send
    - debug_send: Channel obj for sending err_str, send if not None
    - help: str for help_info, replyed in msg.reply
    """
    err_str = f"ERR! [{get_time()}] {def_name} Au:{msg.author_id}\n```\n{excp}\n```"
    _log.exception(f"Exception in {def_name} | Au:{msg.author_id}")
    cm0 = CardMessage()
    c = Card(color='#fb4b57')
    c.append(Module.Header(f"很抱歉，发生了一些错误"))
    c.append(Module.Divider())
    c.append(Module.Section(Element.Text(f"{err_str}\n", Types.Text.KMD)))
    cm0.append(c)
    if send_msg:  # 非{}则执行更新消息，而不是直接发送
        await upd_card(send_msg['msg_id'], cm0, channel_type=msg.channel_type)
    else:
        await msg.reply(cm0)
    # 如果debug_send不是None，则发送信息到报错频道
    if debug_send:
        await bot.client.send(debug_send, err_str)


import psutil, os


async def get_proc_info(start_time=get_time()) -> CardMessage:
    """获取机器人进程信息
    start_time: bot start time str
    """
    p = psutil.Process(os.getpid())
    text = f"霸占的CPU百分比：{p.cpu_percent()} %\n"
    text += f"占用的MEM百分比：{format(p.memory_percent(), '.3f')} %\n"
    text += f"吃下的物理内存：{format((p.memory_info().rss / 1024 / 1024), '.4f')} MB\n"
    text += f"开辟的虚拟内存：{format((p.memory_info().vms / 1024 / 1024), '.4f')} MB\n"
    text += f"IO信息：\n{p.io_counters()}"
    cm = CardMessage()
    c = Card(Module.Header(f"来看看当前的负载吧！"), Module.Context(f"开机于 {start_time} | 记录于 {get_time()}"), Module.Divider(),
             Module.Section(Element.Text(text, Types.Text.KMD)))
    cm.append(c)
    return cm