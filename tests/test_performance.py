import time
from test_catalog import teacher_client


def test_index_cache_reuses_build_and_invalidates_after_save(teacher_client, monkeypatch):
    import backend.main as main
    calls=[]
    original=main.question_links.build
    def build(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(main.question_links,'build',build)
    c=teacher_client
    durations=[]
    for _ in range(2):
        start=time.perf_counter()
        assert c.get('/api/question-library').status_code==200
        durations.append(time.perf_counter()-start)
    assert len(calls)==1
    article=c.post('/api/articles',json={'title':'缓存更新验证文章','genre':'阅读','content':'更新后应立即出现在本人的文章索引。'}).json()['id']
    assert any(a['title']=='缓存更新验证文章' for a in c.get('/api/question-library').json()['articles'])
    assert len(calls)==2
    c.post('/api/register',json={'username':'cache_other','password':'cache-isolation-password-123'})
    assert all(a['title']!='缓存更新验证文章' for a in c.get('/api/question-library').json()['articles'])
    assert len(calls)==3
    print(f'index cold={durations[0]:.3f}s warm={durations[1]:.3f}s')


def test_catalog_compression_and_private_cache_headers(teacher_client):
    c=teacher_client
    response=c.get('/api/catalog',headers={'Accept-Encoding':'gzip'})
    assert response.headers['content-encoding']=='gzip'
    assert response.headers['cache-control']=='no-store'
    assert 'Accept-Encoding' in response.headers['vary']
    assert int(response.headers['content-length']) < len(response.content)*0.6
    print(f'catalog raw={len(response.content)} gzip={response.headers["content-length"]}')
