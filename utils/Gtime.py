from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def get_time(format_str="%y-%m-%d %H:%M:%S"):
    """获取当前时间，格式为 `23-01-01 00:00:00`"""
    a = datetime.now(ZoneInfo('Asia/Shanghai'))  # 返回北京时间
    return a.strftime(format_str)
    # use time.loacltime if you aren't using BeiJing Time
    # return time.strftime("%y-%m-%d %H:%M:%S", time.localtime())


def get_date(format_str="%y-%m-%d"):
    """获取当前日期，格式为 `23-01-01`"""
    a = datetime.now(ZoneInfo('Asia/Shanghai'))  # 返回北京时间
    return a.strftime(format_str)
    # use time.loacltime if you aren't using BeiJing Time
    # return time.strftime("%y-%m-%d", time.localtime())


def get_time_from_stamp(timestamp,format_str="%y-%m-%d %H:%M:%S"):
    """通过时间戳获取当前的本地时间，格式 23-01-01 00:00:00"""
    # localtime = time.localtime(timestamp)
    # localtime_str = time.strftime("%y-%m-%d %H:%M:%S", localtime)
    a = datetime.fromtimestamp(timestamp, tz=ZoneInfo('Asia/Shanghai'))
    return a.strftime(format_str)


def get_timestamp_from_str(time_str:str):
    """从可读时间转为时间戳, 格式 23-01-01 00:00:00"""
    dt = datetime.strptime(time_str, '%y-%m-%d %H:%M:%S')
    tz = timezone(timedelta(hours=8))
    dt = dt.astimezone(tz)
    return dt.timestamp()


def get_date_from_stamp(time_stamp):
    """从时间戳转为可读日期，格式%y-%m-%d"""
    dt = datetime.fromtimestamp(time_stamp)
    tz = timezone(timedelta(hours=8))
    dt = dt.astimezone(tz)
    return dt.strftime("%y-%m-%d")  # 转换成可读时间


def get_datetime_now():
    """获取东八区的datetime对象"""
    a = datetime.now(ZoneInfo('Asia/Shanghai')) # 返回北京时间
    return a