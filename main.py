import io, os
import traceback
import json
import time

from khl import Bot, Event, EventTypes, Message, PublicChannel
from khl.card import Card, CardMessage, Element, Module, Types, Struct

from utils.file.Files import config, _log, bot, StartTime
from utils.log import BotLog
from utils import Gtime, KookApi
from utils.file import SqliteData

debug_ch: PublicChannel = None
"""用于发送错误日志的服务器对象"""


def replace_markdown(nick: str):
    """删除昵称中的转义字符"""
    nick = nick.replace("`", "\\`")  # 替换掉md中的特殊字符
    nick = nick.replace("> ", ">")
    return nick


def is_guild_admin(user_id: str, admin_user: list):
    """判断是否是服务器管理员"""
    return user_id in admin_user


def get_vol_info_card(admin_user_id: str,
                      user_id: str,
                      user_name: str,
                      vol_info: str,
                      role_id="",
                      insert_time=time.time()):
    """获取违例者用户的告示信息
    - 返回两个module的元组
    """
    text = f"违例者：(met){user_id}(met)\n"
    text += f"违例者ID：{user_id}\n"
    text += f"违例者名：{user_name}\n"
    text += f"违例原因：{vol_info}\n"
    text += f"处理人：(met){admin_user_id}(met)\n"
    text += f"处理时间：{Gtime.get_time_from_stamp(insert_time)}"

    sub_text = f"处理人ID：{admin_user_id}"
    if role_id != "": sub_text += f" 违例者角色：{role_id}"

    return (Module.Section(Element.Text(text, Types.Text.KMD)), Module.Context(Element.Text(sub_text, Types.Text.KMD)))


@bot.command(name='vohelp', aliases=['voh'], case_sensitive=False)
async def help_cmd(msg: Message, *arg):
    """帮助命令"""
    try:
        await BotLog.log_msg(msg)
        text = ""
        await msg.reply(await KookApi.get_card_msg(text, sub_text=f"开机于：{StartTime}"))
    except Exception as result:
        await BotLog.base_exception_handler("help", traceback.format_exc(), msg)

@bot.command(name='set-guild',aliases=['配置违例者'])
async def set_guild_conf_cmd(msg:Message,ch_text:str,role_text="e",*arg):
    """配置违例者服务"""
    try:
        await BotLog.log_msg(msg)
        # 参数正确性判断
        if '(chn)' not in ch_text:
            return await msg.reply(await KookApi.get_card_msg("频道参数错误，必须用`#频道`来指定"))
        if role_text != "e" and '(rol)' not in role_text:
            return await msg.reply(await KookApi.get_card_msg("角色组参数错误，必须用`@角色`来指定"))
        # 查询数据
        guild_conf = await SqliteData.query_guild_conf(msg.ctx.guild.id)
        # 已经配置过了，判断是否为服务器管理员
        if guild_conf and not is_guild_admin(msg.author_id, guild_conf['admin_user']):
            return await msg.reply(await KookApi.get_card_msg("您并非当前服务器的违例者管理员", "无权执行本命令"))
        # 将当前用户设置为第一个管理员，如果已经有了，那就使用原来的（当前用户肯定在里面）
        admin_user_list = [msg.author_id] if not guild_conf else guild_conf['admin_user']
        ch_id = ch_text.replace('(chn)','')
        rid = role_text
        # 设置
        bool_ret = await SqliteData.set_guild_conf(msg.ctx.guild.id,admin_user_list,ch_id,role_text)
        # 配置卡片
        header_text = "【违例者管理】初始化" if bool_ret else "【违例者管理】配置更新"
        c = Card(Module.Header(header_text),Module.Divider())
        insert_time = time.time() if not guild_conf else guild_conf['insert_time']
        text = f"管理员用户：{admin_user_list}\n"
        text+= f"违例告示频道：(chn){ch_id}(chn)\n"
        text+= f"违例告示频道ID：{ch_id}\n"
        if role_text != "e":
            text += f"违例者角色：{role_text}\n"
            rid = role_text.replace('(rol)','')
            text += f"违例者角色ID：{rid}\n"
        text+= f"初始化时间：{Gtime.get_time_from_stamp(insert_time)}\n"
        c.append(Module.Section(Element.Text(text, Types.Text.KMD)))
        sub_text = "使用「/添加违例者管理员 @用户」可添加管理员"
        c.append(Module.Context(Element.Text(sub_text, Types.Text.KMD)))
        # 回复用户
        await msg.reply(CardMessage(c))
        _log.info(f"G:{msg.ctx.guild.id} Au:{msg.author_id} | ch:{ch_text} rid:{rid} | is_insert:{bool_ret}")

    except Exception as result:
        await BotLog.base_exception_handler("set-guild", traceback.format_exc(), msg)


@bot.command(name='add-vol', aliases=['新增违例者','添加违例者'])
async def add_vol_cmd(msg: Message, at_user: str, vol_info: str, *arg):
    """新增违例用户的命令"""
    try:
        await BotLog.log_msg(msg)
        guild_conf = await SqliteData.query_guild_conf(msg.ctx.guild.id)
        if not guild_conf:
            return await msg.reply(await KookApi.get_card_msg("当前服务器尚未配置，请使用「/voh」参考帮助命令配置违例者"))
        # 已经配置过了，判断是否为服务器管理员
        if not is_guild_admin(msg.author_id, guild_conf['admin_user']):
            return await msg.reply(await KookApi.get_card_msg("您并非当前服务器的违例者管理员", "无权执行本命令"))
        # 违例者可以通过at或者用户id指定
        vol_user_id = at_user if '(met)' not in at_user else at_user.replace('(met)', '')
        # 尝试获取用户
        vol_user_obj = await msg.ctx.guild.fetch_user(vol_user_id)
        vol_user_name = f"{vol_user_obj.username}#{vol_user_obj.identify_num}"
        # 如果服务器配置role不为空，给用户上角色
        sub_text = "本服务器未设置违例者tag"
        if guild_conf['role_id'] != "":
            await msg.ctx.guild.grant_role(vol_user_obj, int(guild_conf['role_id']))
            sub_text = f"已给用户添加「{guild_conf['role_id']}」违例者角色"
        # 获取成功代表用户id是正确的，可以将数据写入
        await SqliteData.set_violator_log(msg.ctx.guild.id, msg.author_id, vol_user_id, vol_user_name, vol_info,
                                          guild_conf['role_id'])

        # 发送违例者信息到指定频道
        ch = await bot.client.fetch_public_channel(guild_conf['channel_id'])
        vol_card_module = get_vol_info_card(msg.author_id,vol_user_id,vol_user_name,vol_info,guild_conf['role_id'])
        vol_card = Card(Module.Header("告示 | 新增违例者"),Module.Divider())
        for mod in vol_card_module:
            vol_card.append(mod)
        # 发送
        await ch.send(CardMessage(vol_card))
        
        # 写入数据成功，发送信息给用户
        cm = await KookApi.get_card_msg(
            f"操作违例者「{vol_user_name}」成功\n违例信息已经发送至 (chn){guild_conf['channel_id']}(chn)\n", sub_text)
        cm.append(vol_card)
        await msg.reply(cm)
        _log.info(f"G:{msg.ctx.guild.id} Au:{msg.author_id} | add vol_user:{vol_user_id} rid:{guild_conf['role_id']}")
    except Exception as result:
        await BotLog.base_exception_handler("add-vol", traceback.format_exc(), msg)


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