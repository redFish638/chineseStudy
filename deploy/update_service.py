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


def prepare_ownership_schema(env_path=Path('/etc/zhiyu.env')):
    """Use the local database administrator for additive DDL; do not broaden app grants."""
    import shlex
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.engine import make_url
    if not env_path.exists(): return
    values = {}
    for line in env_path.read_text().splitlines():
        parts = shlex.split(line, comments=True)
        if len(parts)==1 and '=' in parts[0]:
            key,value=parts[0].split('=',1);values[key]=value
    raw = values.get('DATABASE_URL','')
    if not raw or not make_url(raw).drivername.startswith('mysql'): return
    url=make_url(raw);probe=create_engine(raw,pool_pre_ping=True)
    additions=[]
    try:
        for table,column,definition in [
            ('zhiyu_articles','owner_id','INTEGER NULL'),
            ('zhiyu_articles','author',"VARCHAR(100) NOT NULL DEFAULT ''"),
            ('zhiyu_bank_materials','owner_id','INTEGER NULL'),
            ('zhiyu_login_sessions','admin_id','INTEGER NULL')]:
            if column not in {x['name'] for x in inspect(probe).get_columns(table)}:
                additions.append(f'ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}')
    finally: probe.dispose()
    if not additions: return
    if url.host not in {'127.0.0.1','localhost',None}:
        raise RuntimeError('远程MySQL需由数据库管理员先执行账号归属字段迁移。')
    result=subprocess.run(['mysql','--protocol=socket','--batch','--database='+url.database,'-e',';\n'.join(additions)+';'],
        capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('本机MySQL管理员未能完成归属字段迁移；服务已停止，数据库记录未删除。')
    print('账号归属字段迁移完成，未增加应用数据库账号权限。',flush=True)


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
    isolating = 'scope_private_records' in (source/'backend/main.py').read_text() and 'scope_private_records' not in (target/'backend/main.py').read_text()
    copied = False
    print('2/4 备份完成，准备更新应用…',flush=True)
    subprocess.run(['systemctl', 'stop', 'zhiyu'], check=True)
    try:
        prepare_ownership_schema()
        copy_code(staging, target)
        copied = True
        subprocess.run(['systemctl', 'start', 'zhiyu'], check=True)
        print('3/4 正在启动应用并初始化独立题库；首次最多等待60秒…',flush=True)
        ready()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8001/', timeout=3) as response:
            if response.status != 200: raise RuntimeError('首页验证失败')
    except BaseException:
        subprocess.run(['systemctl', 'stop', 'zhiyu'], check=False)
        if copied and isolating:
            raise SystemExit('账号隔离升级未完成，后台已停止。为避免旧程序暴露个人资料，未自动回退；请查看 sudo journalctl -u zhiyu -n 40 --no-pager，保留数据库和代码备份。')
        copy_code(backup, target)
        subprocess.run(['systemctl', 'start', 'zhiyu'], check=False)
        raise SystemExit('升级未完成，已尝试恢复旧代码。请查看 sudo journalctl -u zhiyu -n 40 --no-pager；不要重新初始化数据库。')
    print('4/4 代码升级完成，后台健康检查与首页请求通过。')
    print('已有教学数据、教师账号和 /etc/zhiyu.env 已保留；本版本启动时新增独立题库表并初始化公开材料，不重建原数据库。')
    print('旧代码备份：'+str(backup))
    print('请刷新网页并重新登录，进入“文章库”。本机检查不等于公网交互验收。')


if __name__ == '__main__': main()
