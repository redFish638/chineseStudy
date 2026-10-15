"""Apply this release's code-only update; preserve environment values and database records."""
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request
import json

FILES = ['index.html', 'app.js', 'requirements.txt', 'README.md']
APP_DIR = Path('/opt/zhiyu')
SERVICE_PATH = Path('/etc/systemd/system/zhiyu.service')
BACKUP_ROOT = Path('/opt/zhiyu-backups')


def copy_code(source, target):
    target.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copy2(source/name, target/name)
    if (target/'backend').exists():
        shutil.rmtree(target/'backend')
    shutil.copytree(source/'backend', target/'backend', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def ready():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        try:
            with opener.open('http://127.0.0.1:8001/api/health', timeout=2) as response:
                if json.load(response).get('status') == 'ok': return
        except (OSError, ValueError): pass
        time.sleep(.3)
    raise RuntimeError('更新后健康检查未通过')


def main():
    if os.geteuid() != 0: raise SystemExit('请使用 sudo 运行。')
    source = Path(__file__).resolve().parent.parent
    target = APP_DIR
    if not (target/'.venv/bin/python').exists() or not SERVICE_PATH.exists():
        raise SystemExit('未找到已安装的后台，本脚本仅用于升级，未作修改。')
    if target.resolve() != target:
        raise SystemExit('应用目录是符号链接，请先检查，未作修改。')
    if (source/'requirements.txt').read_bytes() != (target/'requirements.txt').read_bytes():
        raise SystemExit('依赖版本有变化，需先规划依赖升级，本次未作修改。')
    print('1/4 正在备份旧代码（保留数据库与账号配置）…',flush=True)
    backup = BACKUP_ROOT/str(time.time_ns())
    backup.mkdir(parents=True, mode=0o700)
    copy_code(target, backup)
    staging = backup/'new-code'
    copy_code(source, staging)
    print('2/4 备份完成，准备更新应用…',flush=True)
    subprocess.run(['systemctl', 'stop', 'zhiyu'], check=True)
    try:
        copy_code(staging, target)
        subprocess.run(['systemctl', 'start', 'zhiyu'], check=True)
        print('3/4 正在启动应用并初始化独立题库；首次最多等待60秒…',flush=True)
        ready()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8001/', timeout=3) as response:
            if response.status != 200: raise RuntimeError('首页验证失败')
    except BaseException:
        subprocess.run(['systemctl', 'stop', 'zhiyu'], check=False)
        copy_code(backup, target)
        subprocess.run(['systemctl', 'start', 'zhiyu'], check=False)
        raise SystemExit('升级未完成，已尝试恢复旧代码。请查看 sudo journalctl -u zhiyu -n 40 --no-pager；不要重新初始化数据库。')
    print('4/4 代码升级完成，后台健康检查与首页请求通过。')
    print('已有教学数据、教师账号和 /etc/zhiyu.env 已保留；本版本启动时新增独立题库表并初始化公开材料，不重建原数据库。')
    print('旧代码备份：'+str(backup))
    print('请刷新网页，进入“选文章 · 自动分析”。本机检查不等于公网交互验收。')


if __name__ == '__main__': main()
