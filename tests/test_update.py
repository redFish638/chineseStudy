from pathlib import Path
from types import SimpleNamespace

import pytest

from deploy import update_service as update


def setup_update(tmp_path, monkeypatch):
    source, target = tmp_path/'source', tmp_path/'installed'
    for folder, text in [(source, 'new'), (target, 'old')]:
        folder.mkdir()
        (folder/'backend').mkdir()
        (folder/'backend/main.py').write_text(text)
        for name in update.FILES:
            (folder/name).write_text('same' if name=='requirements.txt' else text)
    (source/'deploy').mkdir()
    (target/'.venv/bin').mkdir(parents=True)
    (target/'.venv/bin/python').touch()
    (target/'data').mkdir()
    (target/'data/zhiyu.db').write_bytes(b'preserve-existing-database')
    service = tmp_path/'zhiyu.service';service.touch()
    monkeypatch.setattr(update, '__file__', str(source/'deploy/update_service.py'))
    monkeypatch.setattr(update, 'APP_DIR', target)
    monkeypatch.setattr(update, 'SERVICE_PATH', service)
    monkeypatch.setattr(update, 'BACKUP_ROOT', tmp_path/'backups')
    monkeypatch.setattr(update.os, 'geteuid', lambda:0)
    calls=[]
    monkeypatch.setattr(update.subprocess, 'run', lambda args, **kwargs:calls.append(args) or SimpleNamespace(returncode=0))
    return source, target, calls


def test_failed_release_restores_old_code_and_keeps_database(tmp_path, monkeypatch):
    _, target, calls = setup_update(tmp_path, monkeypatch)
    def fail(): raise RuntimeError('simulated startup failure')
    monkeypatch.setattr(update, 'ready', fail)
    with pytest.raises(SystemExit, match='已尝试恢复旧代码'):
        update.main()
    assert (target/'backend/main.py').read_text() == 'old'
    assert (target/'app.js').read_text() == 'old'
    assert (target/'data/zhiyu.db').read_bytes() == b'preserve-existing-database'
    assert calls[-1] == ['systemctl','start','zhiyu']
    assert (next((tmp_path/'backups').iterdir())/'backend/main.py').read_text() == 'old'


def test_dependency_change_stops_before_touching_installed_application(tmp_path, monkeypatch):
    source, target, calls = setup_update(tmp_path, monkeypatch)
    (source/'requirements.txt').write_text('changed-version')
    with pytest.raises(SystemExit, match='依赖版本有变化'):
        update.main()
    assert calls == []
    assert (target/'backend/main.py').read_text() == 'old'
    assert (target/'data/zhiyu.db').read_bytes() == b'preserve-existing-database'


def test_local_mysql_preflight_adds_only_missing_columns_without_granting_app_privileges(tmp_path, monkeypatch):
    import sqlalchemy
    config=tmp_path/'private.env'
    config.write_text('DATABASE_URL="mysql+pymysql://zhiyu_app:dummy-secret@127.0.0.1/chinese_study"\n')
    probe=SimpleNamespace(dispose=lambda:None)
    monkeypatch.setattr(sqlalchemy,'create_engine',lambda *args,**kwargs:probe)
    monkeypatch.setattr(sqlalchemy,'inspect',lambda engine:SimpleNamespace(get_columns=lambda table:[{'name':'id'}]))
    calls=[]
    monkeypatch.setattr(update.subprocess,'run',lambda args,**kwargs:calls.append(args) or SimpleNamespace(returncode=0))
    update.prepare_ownership_schema(config)
    assert len(calls)==1 and calls[0][0]=='mysql'
    sql=calls[0][-1]
    assert sql.count('ALTER TABLE')==4 and 'GRANT' not in sql and 'DROP' not in sql
    assert 'dummy-secret' not in ' '.join(calls[0])
    assert '--database=chinese_study' in calls[0]
    monkeypatch.setattr(sqlalchemy,'inspect',lambda engine:SimpleNamespace(get_columns=lambda table:[{'name':x} for x in ['id','owner_id','author','admin_id']]))
    update.prepare_ownership_schema(config)
    assert len(calls)==1


def test_first_isolation_upgrade_never_restarts_unsafe_old_code_after_new_code_started(tmp_path, monkeypatch):
    source,target,calls=setup_update(tmp_path,monkeypatch)
    (source/'backend/main.py').write_text('scope_private_records')
    monkeypatch.setattr(update,'prepare_ownership_schema',lambda:None)
    monkeypatch.setattr(update,'ready',lambda:(_ for _ in ()).throw(RuntimeError('startup failed')))
    with pytest.raises(SystemExit,match='为避免旧程序暴露个人资料'):
        update.main()
    assert (target/'backend/main.py').read_text()=='scope_private_records'
    assert (target/'data/zhiyu.db').read_bytes()==b'preserve-existing-database'
    assert calls[-1]==['systemctl','stop','zhiyu']
