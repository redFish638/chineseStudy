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
