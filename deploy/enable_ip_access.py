"""Enable the requested HTTP/IP trial entry without replacing other nginx sites."""
import ipaddress
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request


def run(*args):
    return subprocess.run(args, check=True)


def ready():
    for _ in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8001/api/health', timeout=2) as r:
                if r.status == 200:
                    return
        except OSError:
            time.sleep(1)
    raise RuntimeError('应用健康检查未通过')


def main():
    if os.geteuid() != 0:
        raise SystemExit('请使用 sudo 运行。')
    ip = str(ipaddress.IPv4Address(sys.argv[1] if len(sys.argv) > 1 else '49.234.45.134'))
    if not shutil.which('nginx'):
        raise SystemExit('Nginx 尚未安装，请先执行 sudo apt-get install -y nginx。')
    run('systemctl', 'is-active', '--quiet', 'zhiyu')
    ready()
    available = Path('/etc/nginx/sites-available/zhiyu')
    enabled = Path('/etc/nginx/sites-enabled/zhiyu')
    if available.exists() or enabled.exists() or enabled.is_symlink():
        raise SystemExit('知语 Nginx 配置已存在，未覆盖；请反馈此提示。')
    result = subprocess.run(['nginx', '-T'], capture_output=True, text=True, check=True)
    for names in re.findall(r'\bserver_name\s+([^;]+);', result.stdout):
        if ip in names.split():
            raise SystemExit('已有站点使用此 IP，请先核实，未修改配置。')
    envfile = Path('/etc/zhiyu.env')
    old_env = envfile.read_text()
    backup = Path('/etc/zhiyu.env.before-ip-'+str(time.time_ns()))
    # Preserve credentials securely for rollback; never display their values.
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(old_env)
    config = '''# Zhiyu IP trial entry. Managed by deploy/enable_ip_access.py.
server {
    listen 80;
    server_name IP_PLACEHOLDER;
    client_max_body_size 1m;
    access_log off;
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_read_timeout 60s;
    }
}
'''.replace('IP_PLACEHOLDER', ip)
    try:
        with available.open('x') as f:
            f.write(config)
        enabled.symlink_to(available)
        run('nginx', '-t')
        lines = [line for line in old_env.splitlines() if not re.match(r'^\s*(PUBLIC_ORIGIN|COOKIE_SECURE)\s*=', line)]
        new_env = '\n'.join(lines)+f'\nPUBLIC_ORIGIN="http://{ip}"\nCOOKIE_SECURE="false"\n'
        with envfile.open('w') as f:
            f.write(new_env)
        os.chmod(envfile, 0o600)
        run('systemctl', 'restart', 'zhiyu')
        ready()
        run('systemctl', 'enable', '--now', 'nginx')
        run('systemctl', 'reload', 'nginx')
        for path in ('/', '/api/health'):
            req = urllib.request.Request('http://127.0.0.1'+path, headers={'Host': ip})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    raise RuntimeError('网页入口检查失败')
    except BaseException:
        envfile.write_text(old_env)
        os.chmod(envfile, 0o600)
        enabled.unlink(missing_ok=True)
        available.unlink(missing_ok=True)
        subprocess.run(['systemctl', 'restart', 'zhiyu'], check=False)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=False)
        raise SystemExit('入口配置未完成，已尝试恢复原配置。请反馈报错，不要重复初始化数据库。')
    print('IP 网页入口的本机转发检查通过：http://'+ip)
    print('应用后台仍仅监听 127.0.0.1:8001，无需开放8001端口。')
    print('请在自己的浏览器打开上述地址，使用 teacher 和自行设置的密码登录。')
    print('这是未加密的 HTTP 试用入口；公网是否可达及登录仍需浏览器验收。')


if __name__ == '__main__':
    main()
