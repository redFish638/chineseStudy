import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///'+str(tmp_path/'test.db'))
    monkeypatch.setenv('ZHIYU_ADMIN_PASSWORD', 'test-only-password-9843')
    import backend.main as module
    module = importlib.reload(module)
    with TestClient(module.app) as client:
        yield client
    module.engine.dispose()


def login(c):
    assert c.post('/api/login', json={'username': 'teacher', 'password': 'test-only-password-9843'}).status_code == 200


def setup_questions(c):
    login(c)
    a = c.post('/api/articles', json={'title': '测试文章', 'genre': '阅读', 'content': '灯照亮回家的路。'}).json()['id']
    p = c.post('/api/points', json={'article_id': a, 'name': '象征', 'description': '结合文本依据分析情感'}).json()['id']
    questions = []
    for level in ['基础', '巩固', '拓展']:
        q = c.post('/api/questions', json={'point_id': p, 'level': level, 'material': '一盏灯仍然亮着。', 'prompt': '分析灯的意义。', 'reference': '参考答案不应泄漏', 'rubric': '依据与分析各五分', 'max_score': 10})
        assert q.status_code == 200
        questions.append(q.json()['id'])
    return questions


def test_full_teaching_cycle_and_persistence(client):
    c = client
    qs = setup_questions(c)
    a = c.post('/api/assignments', json={'question_id': qs[0], 'student': '学生01'}).json()
    token = a['token']
    c.post('/api/logout')
    task = c.get('/api/tasks/'+token).json()
    assert 'reference' not in task['question'] and 'rubric' not in task['question']
    assert c.post('/api/tasks/'+token+'/submit', json={'answer': '灯象征归家的温暖。'}).status_code == 200
    assert c.post('/api/tasks/'+token+'/submit', json={'answer': '重复作答'}).status_code == 409
    assert 'reference' not in c.get('/api/tasks/'+token).json()['question']
    login(c)
    s = c.get('/api/workspace').json()['submissions'][0]
    review = {'score': 6, 'issue': '缺少文本依据', 'feedback': '请引用灯仍亮着的细节并分析。'}
    assert c.put(f"/api/submissions/{s['id']}/review", json={**review, 'score': 11}).status_code == 422
    assert c.put(f"/api/submissions/{s['id']}/review", json=review).status_code == 200
    follow = c.post('/api/assignments', json={'question_id': qs[1], 'student': '学生01', 'parent_id': a['id']})
    assert follow.status_code == 200
    assert c.post('/api/assignments', json={'question_id': qs[1], 'student': '其他学生', 'parent_id': a['id']}).status_code == 422
    c.post('/api/logout')
    final = c.get('/api/tasks/'+token).json()
    assert final['submission']['score'] == 6
    assert final['question']['reference'] == '参考答案不应泄漏'
    assert final['followups'][0]['token'] == follow.json()['token']
    # Reopen a fresh DB session; records must survive beyond a response/in-memory UI.
    from backend.main import DB, Submission
    from sqlalchemy import select
    with DB() as db:
        assert db.scalar(select(Submission)).answer == '灯象征归家的温暖。'


def test_auth_origin_and_private_files(client):
    c = client
    assert c.get('/api/workspace').status_code == 401
    assert c.post('/api/articles', json={'title': 'x', 'genre': '阅读', 'content': 'x'}).status_code == 401
    assert c.post('/api/login', json={'username': 'teacher', 'password': 'wrong'}).status_code == 401
    assert c.post('/api/login', headers={'origin': 'https://evil.example'}, json={'username': 'teacher', 'password': 'test-only-password-9843'}).status_code == 403
    assert c.get('/.env').status_code == 404
    assert c.get('/data/zhiyu.db').status_code == 404
    assert c.get('/backend/main.py').status_code == 404
    assert c.get('/api/tasks/not-a-valid-token').status_code == 404
    assert c.get('/api/health').json() == {'status': 'ok'}
    assert c.get('/').status_code == 200
    login(c)
    assert 'HttpOnly' in c.cookies.get('zhiyu_session', '') or 'zhiyu_session' in c.cookies
    c.post('/api/logout')
    assert c.get('/api/workspace').status_code == 401


def test_validation_and_followup_constraints(client):
    c = client
    qs = setup_questions(c)
    assert c.post('/api/points', json={'article_id': 999, 'name': '不存在'}).status_code == 404
    assert c.post('/api/questions', json={'point_id': 1, 'level': '错误层次'}).status_code == 422
    a = c.post('/api/assignments', json={'question_id': qs[0], 'student': '01'}).json()
    assert c.post('/api/tasks/'+a['token']+'/submit', json={'answer': '  '}).status_code == 422
    assert c.post('/api/assignments', json={'question_id': qs[1], 'student': '01', 'parent_id': a['id']}).status_code == 422
    c.post('/api/tasks/'+a['token']+'/submit', json={'answer': '作答'})
    assert c.post('/api/assignments', json={'question_id': qs[1], 'student': '01', 'parent_id': a['id']}).status_code == 422


def test_editing_preserves_assigned_question(client):
    c = client
    qs = setup_questions(c)
    workspace = c.get('/api/workspace').json()
    q = workspace['questions'][0]
    body = {k: v for k, v in q.items() if k != 'id'}
    body['prompt'] = '修改后的题干'
    assert c.put(f"/api/questions/{q['id']}", json=body).status_code == 200
    c.post('/api/assignments', json={'question_id': qs[0], 'student': '学生'})
    body['prompt'] = '不应改写学生已收到的题目'
    assert c.put(f"/api/questions/{q['id']}", json=body).status_code == 409
    assert c.get('/api/workspace').json()['questions'][0]['prompt'] == '修改后的题干'
    point = workspace['points'][0]
    assert c.put(f"/api/points/{point['id']}", json={'article_id': point['article_id'], 'name': '修订知识点', 'description': '修订目标'}).status_code == 200
    article = workspace['articles'][0]
    assert c.put(f"/api/articles/{article['id']}", json={'title': '修订文章', 'genre': article['genre'], 'content': article['content']}).status_code == 200
    assert c.post('/api/articles', json={'title': '  ', 'genre': '阅读', 'content': '正文'}).status_code == 422
