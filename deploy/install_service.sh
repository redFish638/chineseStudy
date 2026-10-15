#!/usr/bin/env bash
# First install only. Existing application directories and service units are preserved.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo '请使用 sudo bash deploy/install_service.sh 运行。' >&2
  exit 1
fi
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
target_dir=/opt/zhiyu
if [ ! -f /etc/zhiyu.env ]; then
  echo '缺少 /etc/zhiyu.env，请先完成数据库初始化。' >&2
  exit 1
fi
if [ -e "$target_dir" ] || [ -e /etc/systemd/system/zhiyu.service ]; then
  echo '应用目录或服务已存在，已停止以避免覆盖。请保留现状并反馈此提示。' >&2
  exit 1
fi
if ss -lntH '( sport = :8001 )' | grep -q .; then
  echo '8001 端口已被占用，未安装服务。' >&2
  exit 1
fi
for utility in python3 curl systemctl; do
  command -v "$utility" >/dev/null || { echo "缺少命令：$utility" >&2; exit 1; }
done
if ! id zhiyu >/dev/null 2>&1; then
  useradd --system --user-group --home-dir /opt/zhiyu --no-create-home --shell /usr/sbin/nologin zhiyu
fi
install -d -m 755 "$target_dir"
for file in index.html app.js requirements.txt README.md; do
  install -m 644 "$source_dir/$file" "$target_dir/$file"
done
python3 - "$source_dir" "$target_dir" <<'PY'
import shutil, sys
from pathlib import Path
source, target = map(Path, sys.argv[1:])
shutil.copytree(source/'backend', target/'backend', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
PY
install -d -o zhiyu -g zhiyu -m 700 "$target_dir/data"
python3 -m venv "$target_dir/.venv"
PIP_CONFIG_FILE=/dev/null "$target_dir/.venv/bin/python" -m pip install \
  --no-cache-dir --index-url https://pypi.org/simple -r "$target_dir/requirements.txt"
"$target_dir/.venv/bin/python" -m pip check
install -m 644 "$source_dir/deploy/zhiyu.service" /etc/systemd/system/zhiyu.service
systemctl daemon-reload
systemctl enable --now zhiyu.service
ready=0
for attempt in {1..30}; do
  if curl -fsS --max-time 2 http://127.0.0.1:8001/api/health 2>/dev/null | \
      python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("status")=="ok" else 1)' 2>/dev/null; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo '服务尚未就绪。请执行 sudo systemctl status zhiyu --no-pager 和 sudo journalctl -u zhiyu -n 40 --no-pager 查看原因。' >&2
  echo '不要重复初始化数据库，也不要删除 /etc/zhiyu.env。' >&2
  exit 1
fi
curl -fsS --max-time 5 http://127.0.0.1:8001/ -o /dev/null
printf '\n后台服务已启动，健康检查和首页请求通过。\n'
systemctl is-enabled zhiyu.service
systemctl is-active zhiyu.service
printf '服务目录：/opt/zhiyu\n当前仅监听 127.0.0.1:8001，尚未开放公网入口。\n'
