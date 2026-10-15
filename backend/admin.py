"""Run `python -m backend.admin` in a secure configured server shell to reset teacher password."""
import getpass
from sqlalchemy import delete, select
from .main import Admin, DB, LoginSession, digest


def main():
    username = input('教师账号: ').strip()
    password = getpass.getpass('新密码（至少12位）: ')
    if len(password) < 12 or password != getpass.getpass('再次输入: '):
        raise SystemExit('密码过短或两次输入不一致，未作修改。')
    with DB() as db:
        user = db.scalar(select(Admin).where(Admin.username == username))
        if not user:
            raise SystemExit('账号不存在，未作修改。')
        user.password_hash = digest(password)
        db.execute(delete(LoginSession))
        db.commit()
    print('密码已更新，现有教师会话已退出。')


if __name__ == '__main__':
    main()
