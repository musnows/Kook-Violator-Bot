from .FileManage import FileManage
from ..log.Logging import _log
from ..Gtime import get_time

# 配置相关
config = FileManage("./config/config.json", True)
"""机器人配置文件"""
AdminUser: list[str] = config['admin_user']
"""管理用户列表"""
StartTime = get_time()
"""机器人启动时间"""

# 实例化一个khl的bot，方便其他模组调用
from khl import Bot, Cert

bot = Bot(token=config['bot']['token'])  # websocket
if not config['bot']['ws']:  # webhook
    _log.info(f"[BOT] using webhook at port {config['bot']['webhook_port']}")
    bot = Bot(cert=Cert(token=config['bot']['token'],
                        verify_token=config['bot']['verify_token'],
                        encrypt_key=config['bot']['encrypt']),
              port=config['bot']['webhook_port'])
"""main bot"""
_log.info(f"[BOT] Loading all files")  # 走到这里代表所有文件都打开了
