from main import bot,_log,StartTime

if __name__ == '__main__':
    # 使用本文件启动机器人，方便与其他机器人进程做区分
    _log.info(f"[BOT] Start at {StartTime}")
    bot.run()