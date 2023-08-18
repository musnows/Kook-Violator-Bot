# encoding: utf-8
import os
import json
import time
import sqlite3
import asyncio

from .Files import _log

DBSqlLock = asyncio.Lock()
"""日志操作上锁"""

DB_NAME = 'config/violator.db'
"""sqlite3数据库文件路径"""


class SqliteSql:

    class Table:
        GUILD_CONF_CREATE = "CREATE TABLE IF NOT EXISTS guild_conf(\
                                guild_id TEXT NOT NULL UNIQUE,\
                                admin_user TEXT NOT NULL,\
                                channel_id TEXT NOT NULL,\
                                role_id TEXT NOT NULL DEFAULT '',\
                                insert_time TIMESTAMP DEFAULT (datetime('now', '+8 hours')));"
        """服务器配置表

        - admin_user: 该服务器谁可以处理违规用户,json list
        - channel_id: 配置了哪个频道作为公示频道
        - role_id: 违例者用户tag，可以为空，代表不处理

        """
        VIOLATOR_LOG_CREATE = "CREATE TABLE IF NOT EXISTS violator_log(\
                                guild_id TEXT NOT NULL,\
                                admin_user TEXT NOT NULL,\
                                user_id TEXT NOT NULL,\
                                user_name TEXT NOT NULL,\
                                vol_info TEXT NOT NULL DEFAULT '',\
                                role_id TEXT NOT NULL DEFAULT '',\
                                update_time TIMESTAMP DEFAULT (datetime('now', '+8 hours')),\
                                insert_time TIMESTAMP DEFAULT (datetime('now', '+8 hours')));"
        """违规用户表

        - guild_id: 服务器id
        - admin_user: 处理这个用户的管理员id列表
        - user_id: 违例用户id
        - user_name: 违例用户kook名称
        - vol_info： 为什么被ban
        - role_id: 机器人给他上的违例用户id
        - update_time: 更新时间
        - insert_time: 插入时间

        """

    class Insert:
        INSERT_GUILD_CONF = "INSERT INTO guild_conf (guild_id,admin_user,channel_id,role_id) values (?,?,?,?);"
        """插入GUILD_CONF表, 服务器配置项"""
        INSERT_VIOLATOR_LOG = "INSERT INTO violator_log (guild_id,admin_user,user_id,user_name,vol_info,role_id) \
                                                    values (?,?,?,?,?,?);"
        """插入VIOLATOR_LOG表"""

    class Update:
        UPDATE_VIOLATOR_LOG = "UPDATE violator_log SET admin_user = ?, vol_info = ?, role_id = ?, update_time = ? \
                                                    WHERE guild_id = ? and user_id = ?;"
        """更新VIOLATOR_LOG表，最后两个参数是服务器id和违例用户id"""
        UPDATE_GUILD_CONF = "UPDATE guild_conf SET admin_user = ?, channel_id = ?, role_id = ? \
                                                WHERE guild_id = ?;"
        """更新服务器配置表"""

    class Select:
        SELECT_GUILD_CONF = "select * from guild_conf where guild_id = ?;"
        """搜索guild_conf表"""
        SELECT_VIOLATOR_LOG_UID = "select * from violator_log where guild_id = ? and user_id = ?;"
        """通过id查询违例用户，第二个参数是用户id"""
        SELECT_VIOLATOR_LOG_UNAME = "select * from violator_log where guild_id = ? and user_name LIKE ?;"
        """通过用户ID模糊查询，第二个参数是用户名"""

    class Delete:
        DELETE_VIOLATOR_LOG_UID = "delete from violator_log where guild_id = ? and user_id = ?;"
        """通过服务器id/用户id删除违例者"""


def create_tables(create_tables_sql_list: list[str]):
    """先创建数据库中的表"""
    # list不能为0
    assert (len(create_tables_sql_list) > 0)

    with sqlite3.connect(DB_NAME) as ViolatorDB:
        query = ViolatorDB.cursor()
        for sql in create_tables_sql_list:
            query.execute(sql)
        ViolatorDB.commit()  # 执行

    _log.info(f"[sqlite] create {len(create_tables_sql_list)} tables success")


# 创建数据库中的表
create_tables(
    [SqliteSql.Table.GUILD_CONF_CREATE, SqliteSql.Table.VIOLATOR_LOG_CREATE])


async def set_violator_log(guild_id: str,
                           admin_user_id: str,
                           user_id: str,
                           user_name: str,
                           vol_info: str,
                           role_id="",
                           update_time=time.time()):
    """
    参数
    - 传入服务器id，用户id，管理员用户id，违例原因，违例角色组id
    
    操作
    - 会先查询是否有这个用户，如果有，那就会将管理员用户id给插入到list中
    - 用户存在，会`追加`违例原因

    返回值
    - True（是插入）
    - False（是更新）
    """
    is_insert = True  # 是否是插入
    global DBSqlLock
    async with DBSqlLock:
        with sqlite3.connect(DB_NAME) as db:
            query = db.cursor()
            select_ret = query.execute(
                SqliteSql.Select.SELECT_VIOLATOR_LOG_UID, (guild_id, user_id))
            select_ret_all = select_ret.fetchall()
            if not select_ret_all:  # 没有找到
                query.execute(SqliteSql.Insert.INSERT_VIOLATOR_LOG,
                              (guild_id, json.dumps([admin_user_id]), user_id,
                               user_name, vol_info, role_id))
            else:  # 找到了
                is_insert = False  # 是更新
                # 获取旧值
                admin_user_list = json.loads(
                    select_ret_all[0][1])  # 原本的管理员用户列表
                old_vol_info = select_ret_all[0][4]  # 原本的违例原因
                vol_info = old_vol_info + "\n" + vol_info  # 拼接新违例原因
                # 添加管理员用户
                if admin_user_id not in admin_user_list:
                    admin_user_list.append(admin_user_id)

                # 执行更新sql
                query.execute(SqliteSql.Update.UPDATE_VIOLATOR_LOG,
                              (json.dumps(admin_user_list), vol_info, role_id,
                               update_time, guild_id, user_id))

            db.commit()  # 执行sql
    # 处理完毕，打印
    _log.info(
        f"G:{guild_id} | AAu:{admin_user_id} | Au:{user_id} | rid:{role_id} | violator_log ({is_insert})"
    )
    return is_insert


async def set_guild_conf(guild_id: str,
                         admin_user: list[str],
                         channel_id: str,
                         role_id="e"):
    """配置服务器键值，如果已有，执行更新
    - 如果没有传入role_id，保持旧值不变
    
    返回值
        - True（是插入）
        - False（是更新）
    """
    is_insert = True  # 是否是插入
    global DBSqlLock
    async with DBSqlLock:
        with sqlite3.connect(DB_NAME) as db:
            query = db.cursor()
            select_ret = query.execute(SqliteSql.Select.SELECT_GUILD_CONF,
                                       (guild_id, ))
            select_ret_all = select_ret.fetchall()
            if not select_ret_all:  # 没有找到
                role_id = '' if role_id == 'e' else role_id
                role_id = role_id.replace('(rol)','')
                query.execute(
                    SqliteSql.Insert.INSERT_GUILD_CONF,
                    (guild_id, json.dumps(admin_user), channel_id, role_id))
            else:  # 找到了
                is_insert = False
                admin_user_list = json.loads(
                    select_ret_all[0][1])  # 原本的管理员用户列表
                # role_id 如果没有传入，则采用数据库中原始值
                role_id = select_ret_all[0][3] if role_id == "e" else role_id
                role_id = role_id.replace('(rol)','')  # 因为有点问题，干脆重新替换一下
                # 插入新的管理员用户
                for u in admin_user:
                    if u not in admin_user_list:
                        admin_user_list.append(u)
                # 更新
                query.execute(SqliteSql.Update.UPDATE_GUILD_CONF,
                              (json.dumps(admin_user_list), channel_id, role_id, guild_id))

            db.commit()

    _log.info(
        f"G:{guild_id} | AAu:{admin_user} | C:{channel_id} | rid:{role_id} | guild_conf ({is_insert})"
    )
    return is_insert


async def query_violator_log(guild_id: str, user_id=None, user_name=None):
    """通过用户id或者用户名来查询违例用户
    - 如果提供了user_name参数，则优先使用该参数（不用user_id）
    - 如果需要user_id精准查询，请提供user_id参数并不提供user_name参数
    - 返回包含用户信息的list[dict]，没找到返回空list
    """
    global DBSqlLock
    select_ret_all, user_info_list = None, []
    async with DBSqlLock:
        with sqlite3.connect(DB_NAME) as db:
            query = db.cursor()
            if user_id:
                select_ret = query.execute(
                    SqliteSql.Select.SELECT_VIOLATOR_LOG_UID,
                    (guild_id, user_id))
            elif user_name:
                select_ret = query.execute(
                    SqliteSql.Select.SELECT_VIOLATOR_LOG_UNAME,
                    (guild_id, f"%{user_name}%"))
            # 获取结果
            select_ret_all = select_ret.fetchall()
            if not select_ret_all: return []

            # 设置返回值
            for u in select_ret_all:
                user_info_list.append({
                    "guild_id": u[0],
                    "admin_user": json.loads(u[1]),
                    "user_id": u[2],
                    "user_name": u[3],
                    "vol_info": u[4],
                    "role_id": u[5].replace('(rol)',''),
                    "update_time": u[6],
                    "insert_time": u[7]
                })

    return user_info_list


async def query_guild_conf(guild_id: str):
    """查询服务器配置信息
    - 返回包含服务器信息的dict
    - 没找到返回空dict"""
    global DBSqlLock
    async with DBSqlLock:
        with sqlite3.connect(DB_NAME) as db:
            query = db.cursor()
            select_ret = query.execute(SqliteSql.Select.SELECT_GUILD_CONF,
                                       (guild_id, ))
            select_ret_all = select_ret.fetchall()
            if not select_ret_all: return {}

            return {
                "guild_id": select_ret_all[0][0],
                "admin_user": json.loads(select_ret_all[0][1]),
                "channel_id": select_ret_all[0][2],
                "role_id": select_ret_all[0][3].replace('(rol)',''),
                "insert_time": select_ret_all[0][4]
            }
        
    
async def delete_violator_log(guild_id:str,user_id:str):
    """删除数据库中的违例者记录
    - 删除成功： 返回该用户信息的dict
    - 删除失败： 返回空dict
    """
    query_ret = await query_violator_log(guild_id,user_id=user_id)
    if not query_ret:  # 没有找到
        return {}
    user_info = query_ret[0] # 只会有一个
    # 删除这个用户
    global DBSqlLock
    async with DBSqlLock:
        with sqlite3.connect(DB_NAME) as db:
            query = db.cursor()
            query.execute(SqliteSql.Delete.DELETE_VIOLATOR_LOG_UID,(guild_id,user_id))
            db.commit()  # 执行sql
    # 返回用户信息
    return user_info