# 腾讯云部署说明（待确认服务器连接及 MySQL 配置后执行）

部署目标：Ubuntu，SSH 22，已有项目专用 MySQL。当前没有修改远端服务器。

## 先检查现状

通过腾讯云控制台确认 SSH 服务运行、22 端口监听、安全组和系统防火墙允许管理来源连接。用户确认其他项目可正常连接。当前云开发环境直连返回 Connection refused，经环境代理尝试建立到 22 端口的连接返回 403，均未进入认证。不能据此判断服务器 SSH 未开放；需要可连接该服务器 SSH 的执行环境。环境出口域名/IP 放行配置的保存也未获确认。

登录后先检查系统版本、Python（要求 3.10+）、Nginx、MySQL 版本、现有站点和监听端口。不要覆盖已有站点或重启无关服务。用户已指定新建 `chinese_study`，数据库位于同一服务器。确认 MySQL 管理入口与现有账号，备份数据库后可审核执行 `create_database.sql`，再通过安全管理终端创建独立应用账号。此程序只创建 zhiyu_ 前缀的新表，不导入演示数据、不删除已有表。首次启动前仍应检查是否存在同名前缀的表。

## 安装应用

以下路径是本项目的建议路径，若已存在请先检查内容。创建无登录权限的 zhiyu 服务账号。将项目上传到 /opt/zhiyu（不要上传 .env、开发数据、缓存、Git 元数据或本地虚拟环境），创建 /opt/zhiyu/data 并赋予服务账号读写权限，代码仅需读权限。

```sh
cd /opt/zhiyu
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip check
```

用安全终端编辑 `/etc/zhiyu.env`，参照 `.env.example` 设置配置。文件应由 root 持有，权限 600，由 systemd 读取。不要把服务器 SSH 密码用作应用密码。

MySQL URL 使用 `mysql+pymysql://...`，数据库必须预先存在。URL 内密码特殊字符需百分号编码。账号仅授权项目库的 SELECT、INSERT、UPDATE、DELETE、CREATE、INDEX、REFERENCES 权限，无需 root。远程 MySQL 必须使用服务商要求的 TLS 参数和受信任 CA；不要关闭证书验证。MySQL 8 的认证可由已包含的 cryptography 依赖支持。

教师账号首次启动时创建；之后修改环境变量不会重置数据库里的密码。应用当前是单教师工作区。

## 启动和 HTTPS

检查 `/opt/zhiyu/data` 已创建，服务账号具有权限。将 `zhiyu.service` 安装到 systemd 目录，执行 daemon-reload 和 enable --now。检查 systemctl status、journalctl（不要输出环境变量）及 `curl -fsS http://127.0.0.1:8001/api/health`。

绑定域名并配置合法 TLS 证书，然后以 `nginx.conf` 为模板添加单独站点；替换域名及证书路径，先运行 `nginx -t` 再 reload。安全组仅需公网 443 和证书签发所需的 80；不要公开应用的 8001 或 MySQL 端口。`PUBLIC_ORIGIN` 必须与浏览器访问的 HTTPS 来源完全相同。配置 `COOKIE_SECURE=true`。

没有域名时可通过 SSH 隧道进行本机验证，暂用 `PUBLIC_ORIGIN=http://127.0.0.1:8001`、`COOKIE_SECURE=false`；不建议在公网 HTTP 传输教师密码和学生数据。

## 验收与备份

真实验证：教师登录 → 保存文章和知识点 → 创建基础、巩固、拓展题 → 生成学生任务链接 → 学生在独立浏览器作答 → 教师复核 → 关联同知识点再练 → 学生从原任务查看反馈和再练。

MySQL 使用现有备份机制，并定期恢复验证。SQLite 开发数据不应覆盖生产 MySQL。升级前备份应用和数据库，后续数据库结构升级需迁移方案；当前只提供首版建表，不承诺自动迁移。回滚代码时应保持数据库版本兼容。

任务链接属于持有即可访问的凭证，仅私发对应学生。当前不提供学生账号认证、链接撤销/有效期、多教师隔离和班级批量分发，应按小范围教学试用部署。不要将此版本用于公开开放注册。
