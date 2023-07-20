import io, os
import json
import time

from khl import Bot, Event, EventTypes, Message, PublicChannel
from khl.card import Card, CardMessage, Element, Module, Types, Struct

from utils.file.Files import config, _log, bot, StartTime
from utils.log import BotLog
from utils import Gtime, KookApi

debug_ch:PublicChannel = None
"""用于发送错误日志的服务器对象"""






@bot.on_startup
async def startup_task(b):
    """启动任务"""
    try:
        global debug_ch
        debug_ch = await bot.client.fetch_public_channel(config["debug_ch"])
        _log.info("[BOT.STARTUP] fetch channel success")

        # 走到这里发送信息到debug频道，代表机器人启动
        cm = await KookApi.get_card_msg(f"[BOT.STARTUP] bot up at {StartTime}")
        await debug_ch.send(cm)
        _log.info("[BOT.STARTUP] bot startup")
    except Exception as result:
        _log.exception("[BOT.STARTUP] ERR | Abort!")
        os.abort()


if __name__ == '__main__':
    # 开机的时候打印一次时间，记录开启时间
    _log.info(f"[BOT] Start at {StartTime}")
    bot.run()