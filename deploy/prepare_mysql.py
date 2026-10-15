"""Run with sudo and the project's venv Python. Prepares first-install MySQL configuration."""
import getpass
import os
from pathlib import Path
import secrets
import subprocess
import sys


def mysql(sql):
    result = subprocess.run(['mysql', '--batch', '--skip-column-names'], input=sql, text=True, capture_output=True)
    if result.returncode:
        # Never print SQL or full connector errors: they may contain credential material.
        raise SystemExit('MySQL 管理命令失败；未输出可能包含凭据的错误，请通过 sudo mysql 检查管理权限。')
    return result.stdout.strip()


def env_quote(value):
    return '"'+value.replace('\\', '\\\\').replace('"', '\\"')+'"'


def main():
    if os.geteuid() != 0:
        raise SystemExit('请使用 sudo 运行此脚本。')
    target = Path('/etc/zhiyu.env')
    if target.exists():
        raise SystemExit('/etc/zhiyu.env 已存在，已停止以保留现有配置。')
    if mysql("SELECT COUNT(*) FROM mysql.user WHERE User='zhiyu_app' AND Host='localhost';") != '0':
        raise SystemExit('zhiyu_app 账号已存在，已停止，未重置密码。')
    if mysql("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='chinese_study';") != '0':
        raise SystemExit('chinese_study 数据库已存在，已停止，请先确认其中的数据。')
    password = getpass.getpass('设置教师登录密码（至少12位，输入不显示）: ')
    if len(password) < 12 or len(password) > 200:
        raise SystemExit('密码需为12至200位，未作修改。')
    if password != getpass.getpass('再次输入教师登录密码: '):
        raise SystemExit('两次密码不一致，未作修改。')
    database_password = secrets.token_hex(32)
    values = {
        'DATABASE_URL': f'mysql+pymysql://zhiyu_app:{database_password}@127.0.0.1:3306/chinese_study?charset=utf8mb4',
        'ZHIYU_ADMIN_USER': 'teacher',
        'ZHIYU_ADMIN_PASSWORD': password,
        'PUBLIC_ORIGIN': 'http://127.0.0.1:8001',
        'COOKIE_SECURE': 'false',
    }
    # Reserve the configuration path before MySQL's auto-committing DDL runs.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(''.join(key+'='+env_quote(value)+'\n' for key, value in values.items()))
        f.flush()
        os.fsync(f.fileno())
    mysql("CREATE DATABASE chinese_study CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
          f"CREATE USER 'zhiyu_app'@'localhost' IDENTIFIED BY '{database_password}';\n"
          "GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, REFERENCES ON chinese_study.* TO 'zhiyu_app'@'localhost';")
    try:
        import pymysql
        with pymysql.connect(host='127.0.0.1', user='zhiyu_app', password=database_password, database='chinese_study', charset='utf8mb4') as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT DATABASE(), CURRENT_USER()')
                database, user = cursor.fetchone()
    except Exception:
        raise SystemExit('配置已保存，但应用账号连接验证失败。请保留 /etc/zhiyu.env，不要重复运行初始化。')
    print('数据库已创建：'+database)
    print('应用账号连接验证通过：'+user)
    print('配置已保存：/etc/zhiyu.env（仅 root 可读写）')
    print('教师账号：teacher；密码为刚才自行设置的密码。')
    print('当前仅配置本机访问，下一步安装后台服务及配置网页入口。')


if __name__ == '__main__':
    main()
