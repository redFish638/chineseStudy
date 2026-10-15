"""Enable the requested HTTP/IP trial entry without replacing other nginx sites."""
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error


def run(*args):
    return subprocess.run(args, check=True)


# All checks target loopback. They must not inherit HTTP proxy settings.
LOCAL_HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def wait_http(url, host=None, homepage=False, timeout=30):
    deadline = time.monotonic()+timeout
    last = '尚无响应'
    while time.monotonic() < deadline:
        try:
            request = urllib.request.Request(url, headers={'Host': host} if host else {})
            with LOCAL_HTTP.open(request, timeout=2) as response:
                body = response.read(200000).decode('utf-8')
                valid = ('知语' in body and 'app.js' in body) if homepage else json.loads(body).get('status') == 'ok'
                if response.status == 200 and valid:
                    return
                last = '响应不是预期的知语页面或健康状态'
        except urllib.error.HTTPError as exc:
            last = 'HTTP '+str(exc.code)
        except (OSError, ValueError, AttributeError) as exc:
            last = type(exc).__name__
        time.sleep(0.1)
    raise RuntimeError('本机入口就绪检查超时：'+last)


def ready():
    wait_http('http://127.0.0.1:8001/api/health')


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
    stage = '写入 Nginx 站点'
    created_available = created_enabled = False
    try:
        with available.open('x') as f:
            f.write(config)
        created_available = True
        enabled.symlink_to(available)
        created_enabled = True
        stage = '检查 Nginx 配置语法'
        run('nginx', '-t')
        lines = [line for line in old_env.splitlines() if not re.match(r'^\s*(PUBLIC_ORIGIN|COOKIE_SECURE)\s*=', line)]
        new_env = '\n'.join(lines)+f'\nPUBLIC_ORIGIN="http://{ip}"\nCOOKIE_SECURE="false"\n'
        with envfile.open('w') as f:
            f.write(new_env)
        os.chmod(envfile, 0o600)
        stage = '重新启动知语后台'
        run('systemctl', 'restart', 'zhiyu')
        ready()
        stage = '启动和重载 Nginx'
        run('systemctl', 'enable', '--now', 'nginx')
        run('systemctl', 'reload', 'nginx')
        # Reload is graceful: old workers may still answer until new workers are ready.
        stage = '等待 Nginx 新配置提供知语入口'
        wait_http('http://127.0.0.1/api/health', host=ip)
        wait_http('http://127.0.0.1/', host=ip, homepage=True)
    except BaseException as exc:
        reason = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        print('失败阶段：'+stage, file=sys.stderr)
        print('诊断：'+reason, file=sys.stderr)
        rollback_errors = []
        try:
            envfile.write_text(old_env)
            os.chmod(envfile, 0o600)
            if created_enabled:
                enabled.unlink(missing_ok=True)
            if created_available:
                available.unlink(missing_ok=True)
        except OSError:
            rollback_errors.append('配置文件恢复失败')
        for service_action in [('restart', 'zhiyu'), ('reload', 'nginx')]:
            result = subprocess.run(['systemctl', *service_action], check=False)
            if result.returncode:
                rollback_errors.append(' '.join(service_action)+' 失败')
        if rollback_errors:
            print('回滚需检查：'+'；'.join(rollback_errors), file=sys.stderr)
        raise SystemExit('入口配置未完成，已尝试恢复原配置。请保留以上诊断，不要重新初始化数据库。')
    print('IP 网页入口的本机转发检查通过：http://'+ip)
    print('应用后台仍仅监听 127.0.0.1:8001，无需开放8001端口。')
    print('请在自己的浏览器打开上述地址，使用 teacher 和自行设置的密码登录。')
    print('这是未加密的 HTTP 试用入口；公网是否可达及登录仍需浏览器验收。')


if __name__ == '__main__':
    main()
