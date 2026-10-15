import importlib
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import analysis, catalog


@pytest.fixture()
def teacher_client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///'+str(tmp_path/'library.db'))
    monkeypatch.setenv('ZHIYU_ADMIN_PASSWORD', 'test-only-password-9843')
    for key in ['ZHIYU_AI_API_KEY', 'ZHIYU_AI_BASE_URL', 'ZHIYU_AI_MODEL']:
        monkeypatch.delenv(key, raising=False)
    import backend.main as module
    module = importlib.reload(module)
    with TestClient(module.app) as client:
        assert client.get('/api/catalog').status_code == 401
        client.post('/api/login', json={'username': 'teacher', 'password': 'test-only-password-9843'})
        yield client
    module.engine.dispose()


def test_catalog_selection_preview_confirmation_and_practice(teacher_client):
    c = teacher_client
    library = c.get('/api/catalog').json()
    assert len(library['items']) >= 8
    assert library['ai_configured'] is False
    assert any('GAOKAO' in x['name'] for x in library['resources'])
    assert all('points' not in x for x in library['items'])
    article_id = c.post('/api/catalog/deng-gao/open').json()['id']
    assert c.post('/api/catalog/deng-gao/open').json()['id'] == article_id
    result = c.post(f'/api/articles/{article_id}/analyze', json={}).json()
    assert result['source'] == '内置教研解析（非AI）'
    assert '万里悲秋常作客' in result['points'][2]['evidence']
    assert c.get('/api/workspace').json()['points'] == []
    body = {k: result[k] for k in ['source', 'article_digest', 'points']}
    saved = c.post(f'/api/articles/{article_id}/confirm-analysis', json=body)
    assert saved.json()['created'] == 3
    assert c.post(f'/api/articles/{article_id}/confirm-analysis', json=body).json() == {'created': 0, 'skipped': 3}
    point = c.get('/api/workspace').json()['points'][0]
    assert '原文依据：' in point['description'] and '拓展：' in point['description']
    candidates = c.get(f"/api/points/{point['id']}/practice-candidates").json()['items']
    assert {x['level'] for x in candidates} == {'基础', '巩固', '拓展'}
    assert all('非高考真题' in x['source'] or 'GAOKAO-Bench' in x['source'] for x in candidates)
    assert all(x['material'] != catalog.get_entry('deng-gao')['content'] for x in candidates)
    assert c.post('/api/catalog/no-such-entry/open').status_code == 404


def test_stale_or_invented_analysis_cannot_be_saved(teacher_client):
    c = teacher_client
    id = c.post('/api/catalog/shi-shuo/open').json()['id']
    result = c.post(f'/api/articles/{id}/analyze', json={}).json()
    body = {k: result[k] for k in ['source', 'article_digest', 'points']}
    body['points'][0]['evidence'] = '原文中不存在的句子'
    assert c.post(f'/api/articles/{id}/confirm-analysis', json=body).status_code == 422
    body['points'][0]['evidence'] = catalog.get_entry('shi-shuo')['points'][0]['evidence']
    article = c.get('/api/workspace').json()['articles'][0]
    c.put(f'/api/articles/{id}', json={'title': article['title'], 'genre': article['genre'], 'content': article['content']+'修改'})
    assert c.post(f'/api/articles/{id}/confirm-analysis', json=body).status_code == 409
    assert c.post(f'/api/articles/{id}/analyze', json={}).status_code == 422
    assert c.get('/api/workspace').json()['points'] == []


def test_ai_provider_validation_and_no_silent_fallback(monkeypatch):
    article = SimpleNamespace(title='测试', genre='诗歌', content='月出惊山鸟，时鸣春涧中。')
    monkeypatch.setenv('ZHIYU_AI_BASE_URL', 'https://provider.example/v1')
    monkeypatch.setenv('ZHIYU_AI_MODEL', 'test-model')
    monkeypatch.setenv('ZHIYU_AI_API_KEY', 'test-provider-key')
    point = dict(catalog.get_entry('niao-ming-jian')['points'][0])
    captured = []

    class MockClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            captured.append(kwargs)
            import json
            return httpx.Response(200, request=httpx.Request('POST', url), json={'choices': [{'message': {'content': json.dumps({'points': [point]})}}]})

    monkeypatch.setattr(analysis.httpx, 'Client', MockClient)
    result = analysis.analyze(article, 'ai')
    assert result['source'] == 'AI辅助解析'
    assert captured[0]['json']['model'] == 'test-model'
    point['evidence'] = '不存在的引用'
    with pytest.raises(RuntimeError, match='引文'):
        analysis.analyze(article, 'ai')
    monkeypatch.setenv('ZHIYU_AI_BASE_URL', 'http://provider.example')
    with pytest.raises(ValueError, match='HTTPS'):
        analysis.analyze(article, 'ai')


def test_public_exam_material_and_original_questions(teacher_client):
    c = teacher_client
    items = c.get('/api/catalog').json()['items']
    exam_entries = [x for x in items if x['collection'] == '公开真题材料']
    assert len(exam_entries) == 57
    assert sum(x['genre']=='诗歌' for x in exam_entries)==29
    entry = exam_entries[0]
    article_id = c.post('/api/catalog/'+entry['id']+'/open').json()['id']
    result = c.post(f'/api/articles/{article_id}/analyze', json={}).json()
    assert result['source'] == '公开题目解析提取（非AI）'
    assert all(p['evidence'] in entry['content'] for p in result['points'])
    body = {k: result[k] for k in ['source', 'article_digest', 'points']}
    assert c.post(f'/api/articles/{article_id}/confirm-analysis', json=body).status_code == 200
    p = c.get('/api/workspace').json()['points'][0]
    candidates = c.get(f"/api/points/{p['id']}/practice-candidates").json()['items']
    originals = [x for x in candidates if 'GAOKAO-Bench' in x['source']]
    assert originals and originals[0]['reference']
    assert '系统建议' in originals[0]['source']
