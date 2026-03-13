# -*- coding: utf-8 -*-
import subprocess
import os
import fcntl

def runcmd(cmd, cwd=None, timeout=None):
    '''
    用于执行命令行cmd命令，如果命令执行出错或者超时则输出相应信息，
    这里接受的cmd是一个string, cwd是当前工作路径
    '''
    try:
        ret = subprocess.run(cmd, cwd=cwd, capture_output=True, shell=True, timeout=timeout)
        if ret.returncode == 0:
            flag = True
        else:
            flag = False
    except Exception as e:
        flag = False
        ret = None
    return flag, ret

def create_file(output):
    # 获取文件锁
    with open(output, "w") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        # 检查文件是否已经存在
        script_content = '#!/bin/bash\necho "fake build!"\n'
        file.write(script_content)
        os.chmod(output, 0o755)
        # 释放文件锁
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)
