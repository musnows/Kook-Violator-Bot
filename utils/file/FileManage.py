import asyncio
import json
import os

import aiofiles

from ..log.Logging import _log

FileList = []
"""files need to write into storage"""
FlieSaveLock = asyncio.Lock()
"""files save lock, using in save_all_file"""


def open_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        tmp = json.load(f)
    return tmp


async def write_file_aio(path: str, value):
    async with aiofiles.open(path, 'w+', encoding='utf-8') as f:
        await f.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def write_file(path: str, value):
    with open(path, 'w+', encoding='utf-8') as fw2:
        json.dump(value, fw2, indent=2, sort_keys=True, ensure_ascii=False)


async def save_all_file(is_Aio=True):
    """save all file in FileList
    """
    # 加锁，避免数据写入错误
    global FlieSaveLock
    async with FlieSaveLock:
        for i in FileList:
            try:
                if is_Aio:
                    await i.save_aio()
                else:
                    i.save()
            except:
                _log.exception(f"save.all.file | {i.path}")


# 文件管理类
class FileManage:
    # 初始化构造
    def __init__(self, path: str, read_only: bool = False, default_value=None) -> None:
        """
        - path: 文件路径，仅支持相对路径，如`./test.json`
        - read_only: 文件是否是只读（只读文件不会被定时保存）
        """
        assert ('/' in path)  # 必须要有至少1个/作为分隔符
        # 文件路径是否存在，如果不存在，并且配置了默认值，那就创建他
        if not os.path.exists(path) and default_value:
            write_file(path,default_value)  
            tmp = default_value  # 写回的时候会w+创建文件
            _log.info(f"creating [{path}] with default | {default_value}")
        else:
            with open(path, 'r', encoding='utf-8') as f:
                tmp = json.load(f)
        self.value = tmp  # 值
        self.type = type(tmp)  # 值的类型
        self.path = path  # 值的文件路径
        self.Ronly = read_only  # 是否只读
        # 将自己存全局变量里面
        if not read_only:
            global FileList  # 如果不是只读，那就存list里面
            FileList.append(self)

    # []操作符重载
    def __getitem__(self, index):
        return self.value[index]

    # 打印重载
    def __str__(self) -> str:
        return str(self.value)

    # 删除成员
    def __delitem__(self, index):
        del self.value[index]

    # 长度
    def __len__(self):
        return len(self.value)

    # 索引赋值 x[i] = 1
    def __setitem__(self, index, value):
        self.value[index] = value

    # 迭代
    def __iter__(self):
        return self.value.__iter__()

    def __next__(self):
        return self.value.__next__()

    # 比较==
    def __eq__(self, i):
        if isinstance(i, FileManage):
            return self.value.__eq__(i.value)
        else:
            return self.value.__eq__(i)

    # 比较!=
    def __ne__(self, i):
        if isinstance(i, FileManage):
            return self.value.__ne__(i.value)
        else:
            return self.value.__ne__(i)

    # 获取成员
    def get_instance(self):
        return self.value

    # 遍历dict
    def items(self):
        return self.value.items()

    # 追加
    def append(self, i):
        self.value.append(i)

    # list的删除
    def remove(self, i):
        self.value.remove(i)

    def keys(self):
        return self.value.keys()

    # 保存
    def save(self):
        with open(self.path, 'w+', encoding='utf-8') as fw:
            json.dump(self.value, fw, indent=2, sort_keys=True, ensure_ascii=False)

    # 异步保存
    async def save_aio(self):
        async with aiofiles.open(self.path, 'w+', encoding='utf-8') as f:  # 这里必须用dumps
            await f.write(json.dumps(self.value, indent=2, sort_keys=True, ensure_ascii=False))
