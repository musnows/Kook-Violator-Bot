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


def is_bot_admin(user_id: str):
    """是否是机器人的管理员"""
    return user_id in config['admin_user']


def is_guild_admin(user_id: str, admin_user: list):
    """判断是否是服务器管理员"""
    return user_id in admin_user


def get_vol_info_card(admin_user_list: list[str],
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
    text += f"处理人："
    for admin_user_id in admin_user_list:
        text += f"(met){admin_user_id}(met) "
    text += "\n"
    text += f"处理时间：{Gtime.get_time_from_stamp(insert_time)}"
    # 底部text
    sub_text = f"处理人ID：{admin_user_list}"
    if role_id != "": sub_text += f"  违例者角色：{role_id}"

    return (Module.Section(Element.Text(text, Types.Text.KMD)), Module.Context(Element.Text(sub_text, Types.Text.KMD)))


@bot.command(name='vohelp', aliases=['voh'], case_sensitive=False)
async def help_cmd(msg: Message, *arg):
    """帮助命令"""
    try:
        await BotLog.log_msg(msg)
        text = "「/配置违例者 #频道」初始化违例者管理，将在目标频道发送违例者公告\n"
        text += "「/配置违例者 #频道 @角色」同上，添加违例者时会添加上这个角色\n"
        text += "「/添加违例者管理员 @用户」添加其他违例者管理员\n"
        text += "「/添加违例者 @违例者用户 违例原因」新增违例者\n"
        text += " **查询违例者的三种办法**\n"
        text += "「/查询违例者 违例者用户名」通过用户名模糊匹配搜索\n"
        text += "「/查询违例者 @用户」精准查询\n"
        text += "「/查询违例者 用户ID -id」通过用户ID来精准查询"
        # 构造卡片并发送
        c = Card(Module.Header("违例者管理机器人的帮助命令"), Module.Context(f"开机于：{StartTime}"), Module.Divider())
        c.append(Module.Section(Element.Text(text, Types.Text.KMD)))
        c.append(Module.Container(Element.Image(src="https://img.kookapp.cn/assets/2023-07/jJ4cBQIOnl0i30c0.png")))
        await msg.reply(CardMessage(c))
    except Exception as result:
        await BotLog.base_exception_handler("help", traceback.format_exc(), msg)


@bot.command(name='set-guild', aliases=['配置违例者'])
async def set_guild_conf_cmd(msg: Message, ch_text: str, role_text="e", *arg):
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
        ch_id = ch_text.replace('(chn)', '')
        rid = role_text
        # 设置
        bool_ret = await SqliteData.set_guild_conf(msg.ctx.guild.id, admin_user_list, ch_id, role_text)
        # 配置卡片
        header_text = "【违例者管理】初始化" if bool_ret else "【违例者管理】配置更新"
        c = Card(Module.Header(header_text), Module.Divider())
        insert_time = time.time() if not guild_conf else guild_conf['insert_time']
        text = f"管理员用户：{admin_user_list}\n"
        text += f"违例告示频道：(chn){ch_id}(chn)\n"
        text += f"违例告示频道ID：{ch_id}\n"
        if role_text != "e":
            text += f"违例者角色：{role_text}\n"
            rid = role_text.replace('(rol)', '')
            text += f"违例者角色ID：{rid}\n"
        text += f"初始化时间：{Gtime.get_time_from_stamp(insert_time)}\n"
        c.append(Module.Section(Element.Text(text, Types.Text.KMD)))
        sub_text = "使用「/添加违例者管理员 @用户」可添加管理员"
        c.append(Module.Context(Element.Text(sub_text, Types.Text.KMD)))
        # 回复用户
        await msg.reply(CardMessage(c))
        _log.info(f"G:{msg.ctx.guild.id} Au:{msg.author_id} | ch:{ch_text} rid:{rid} | is_insert:{bool_ret}")

    except Exception as result:
        await BotLog.base_exception_handler("set-guild", traceback.format_exc(), msg)


@bot.command(name='add-guild-admin', aliases=['添加违例者管理员'])
async def add_guild_admin_cmd(msg: Message, at_user: str, *arg):
    """添加违例者管理员"""
    try:
        await BotLog.log_msg(msg)
        if '(met)' not in at_user:
            return await msg.reply(await KookApi.get_card_msg("用户参数错误，必须用`@用户`来指定新管理员"))
        # 查询服务器配置
        guild_conf = await SqliteData.query_guild_conf(msg.ctx.guild.id)
        if not guild_conf:
            return await msg.reply(await KookApi.get_card_msg("当前服务器尚未配置，请使用「/voh」参考帮助命令配置违例者"))
        # 插入管理员
        target_user_id = at_user.replace('(met)', '')
        text = f'管理员「{at_user}」已存在\n用户ID：{target_user_id}\n'
        admin_user_list = guild_conf['admin_user']
        if target_user_id not in admin_user_list:
            admin_user_list.append(target_user_id)
            text = f'新管理员「{at_user}」添加成功\n用户ID：{target_user_id}\n'
        text += f"当前服务器管理员列表：\n```\n{admin_user_list}\n```"
        # 设置数据库后回复用户
        await SqliteData.set_guild_conf(msg.ctx.guild.id, admin_user_list, guild_conf['channel_id'],
                                        guild_conf['role_id'])

        await msg.reply(await KookApi.get_card_msg(text))
        _log.info(f"G:{msg.ctx.guild.id} AAu:{msg.author_id} | add admin:{target_user_id}")
    except Exception as result:
        await BotLog.base_exception_handler("set-guild", traceback.format_exc(), msg)


@bot.command(name='add-vol', aliases=['新增违例者', '添加违例者'])
async def add_vol_cmd(msg: Message, at_user: str, vol_info: str, *arg):
    """新增违例用户的命令"""
    try:
        await BotLog.log_msg(msg)
        guild_conf = await SqliteData.query_guild_conf(msg.ctx.guild.id)
        if not guild_conf:
            return await msg.reply(await KookApi.get_card_msg("当前服务器尚未配置，请使用「/voh」参考帮助命令配置违例者管理"))
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
        vol_card_module = get_vol_info_card([msg.author_id], vol_user_id, vol_user_name, vol_info,
                                            guild_conf['role_id'])
        vol_card = Card(Module.Header("告示 | 新增违例者"), Module.Divider())
        for mod in vol_card_module:
            vol_card.append(mod)
        # 发送
        await ch.send(CardMessage(vol_card))

        # 写入数据成功，发送信息给用户
        cm = await KookApi.get_card_msg(f"操作违例者「{vol_user_name}」成功\n违例信息已经发送至 (chn){guild_conf['channel_id']}(chn)\n",
                                        sub_text)
        cm.append(vol_card)
        await msg.reply(cm)
        _log.info(f"G:{msg.ctx.guild.id} Au:{msg.author_id} | add vol_user:{vol_user_id} rid:{guild_conf['role_id']}")
    except Exception as result:
        await BotLog.base_exception_handler("add-vol", traceback.format_exc(), msg)


@bot.command(name='search-vol', aliases=['查询违例者'])
async def search_vol_cmd(msg: Message, at_user: str, *arg):
    """查询违例者的命令，可以通过用户名、at用户、用户ID来查询"""
    try:
        await BotLog.log_msg(msg)
        guild_conf = await SqliteData.query_guild_conf(msg.ctx.guild.id)
        if not guild_conf:
            return await msg.reply(await KookApi.get_card_msg("当前服务器尚未配置，请使用「/voh」参考帮助命令配置违例者管理"))
        # 已经配置过了，判断是否为服务器管理员
        if not is_guild_admin(msg.author_id, guild_conf['admin_user']):
            return await msg.reply(await KookApi.get_card_msg("您并非当前服务器的违例者管理员", "无权执行本命令"))
        # 判断是用用户id查询，还是用户名
        target_user_id = "N/A"
        if '(met)' in at_user:
            target_user_id = at_user.replace('(met)', '')
        elif '-id' in arg:
            target_user_id = at_user
        # 如果用户id为空，则采用用户名查询
        if target_user_id == "N/A":
            query_ret = await SqliteData.query_violator_log(msg.ctx.guild.id, user_name=at_user)
        else:
            query_ret = await SqliteData.query_violator_log(msg.ctx.guild.id, target_user_id)
        # 没有查到
        if not query_ret:
            return await msg.reply(await KookApi.get_card_msg(f"目标「{at_user}」不存在", f"目标用户ID：{target_user_id}"))
        # 查到了
        cm,c = CardMessage(),Card(Module.Header(f"目标「{at_user}」查询结果如下"))
        for vol_user in query_ret:
            vol_card_module = get_vol_info_card(vol_user['admin_user'], vol_user['user_id'], vol_user['user_name'],
                                    vol_user['vol_info'], vol_user['role_id'], vol_user['update_time'])
            for mod in vol_card_module:
                c.append(mod)
        # 回复用户
        cm.append(c)
        await msg.reply(cm)
        _log.info(f"G:{msg.ctx.guild.id} Au:{msg.author_id} | search:{at_user} {target_user_id}")
    except Exception as result:
        await BotLog.base_exception_handler("search-vol", traceback.format_exc(), msg)


#########################################################################################


@bot.command(name='kill', aliases=['下线'])
async def kill_bot_cmd(msg: Message, at_text="", *arg):
    """机器人下线"""
    try:
        await BotLog.log_msg(msg)  # 这个命令必须要at机器人
        if not is_bot_admin(msg.author_id):
            return  # 直接退出，非管理
        if f'(met){bot.me.id}(met)' not in at_text:
            return  # 需要at机器人才能kill，不做提示

        # 申请锁，保证没有数据库操作，能成功退出
        async with SqliteData.DBSqlLock:
            await msg.reply(await KookApi.get_card_msg("[KILL] 保存全局变量成功，bot下线"))
            ret = "webhook"
            if config['bot']['ws']:
                ret = await KookApi.bot_offline()
            # 打印日志后下线
            _log.fatal(f"KILL | bot-off | {ret}\n")
            os._exit(0)  # 退出程序

    except Exception as result:
        await BotLog.base_exception_handler("kill", traceback.format_exc(), msg)

# 配置项中存在才启动这个task
if 'uptime_url' in config and 'http' in config['uptime_url']:
    import requests
    uptime_count = 0 # 计数器
    # 直接请求一次
    _log.info(f"[BOT.TASK] add uptime task | {requests.get(url=config['uptime_url']).status_code}")
    # 添加任务
    @bot.task.add_interval(seconds=80)
    async def ping_alive_task():
        """uptime监控"""
        try:
            global uptime_count
            ret = requests.get(url=config['uptime_url'])
            # 每5次打印一次输出
            uptime_count +=1
            if uptime_count>=5:
                uptime_count = 0
                _log.info(f"uptime {config['uptime_url']} | status:{ret.status_code}")
            
        except Exception as result:
            _log.exception("err in ping task")

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