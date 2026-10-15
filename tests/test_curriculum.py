from backend import bank, catalog
from test_catalog import teacher_client


def test_curriculum_coverage_and_truthful_availability(teacher_client):
    data=teacher_client.get('/api/catalog').json()
    items=data['items']
    assert len(items)==961
    assert data['readable']==905
    assert data['analyzable']==905
    assert sum(x['recommended'] for x in items)==72
    assert set(data['books'])=={'必修上册','必修下册','选择性必修上册','选择性必修中册','选择性必修下册'}
    assert len({x['id'] for x in items})==len(items)
    assert all(x['available']==bool(x['content'].strip()) for x in items)
    assert all(not x['has_analysis'] or x['available'] for x in items)
    for title in ['红楼梦','乡土中国','插秧歌','在民族复兴的历史丰碑上——2020中国抗疫记','风景谈','一个消逝了的山村']:
        assert any(x['title']==title and x['books'] for x in items)
    chapter=next(x for x in items if x['title']=='《论语》十二章')
    assert len(chapter['content'].splitlines())==12
    assert '克己复礼为仁' in chapter['content'] and '有一言而可以终身行之者乎' in chapter['content']
    assert '温故而知新' not in chapter['content']  # Do not mislabel the junior-school selection.
    assert any(x['title']=='大学之道' for x in items)
    assert any(x['title']=='大学（节选）' for x in items)
    assert all('2020' in x['directory_note'] for x in items if x['recommended'] and x.get('curriculum_added'))


def test_directory_cannot_create_blank_article_and_readable_uses_authored_analysis(teacher_client):
    c=teacher_client
    items=c.get('/api/catalog').json()['items']
    directory=next(x for x in items if x['title']=='百年孤独（节选）')
    before=c.get('/api/workspace').json()['articles']
    assert c.post('/api/catalog/'+directory['id']+'/open').status_code==409
    assert c.get('/api/workspace').json()['articles']==before
    original=next(x for x in items if x['title']=='陈情表')
    result=c.post('/api/catalog/'+original['id']+'/open').json()
    assert result['has_analysis'] is True
    assert c.post('/api/catalog/'+original['id']+'/open').json()['id']==result['id']
    response=c.post(f"/api/articles/{result['id']}/analyze",json={})
    assert response.status_code==200
    assert response.json()['source']=='内置篇目解析（待审校）'
    assert any(p['name']=='比喻与情境压力' and '日薄西山' in p['evidence'] for p in response.json()['points'])
    assert c.get('/api/workspace').json()['points']==[]


def test_expansion_keeps_legacy_bank_ids_and_questions_and_adds_readable_curriculum_only():
    records=bank.seed_records()
    assert len(records)==1345
    assert len({x['id'] for x in records})==1345
    assert sum(len(x['questions']) for x in records)==270
    assert sum(x['id'].startswith('curated:') for x in records)==9
    assert sum(x['id'].startswith('poetry:tang:') for x in records)==365
    additions=[x for x in records if x['id'].startswith('curriculum:')]
    assert len(additions)==91
    assert all(x['body'].strip() and x['notes'] and not x['questions'] for x in additions)
    assert len({x['content_hash'] for x in additions})==len(additions)


def test_edition_specific_placement_does_not_relabel_recommendations_or_exams(teacher_client):
    data = teacher_client.get('/api/catalog').json()
    editions = {e['id']: e for e in data['editions']}
    assert editions['renjiao']['publisher'] == '人民教育出版社'
    assert editions['sujiao']['publisher'] == '江苏教育出版社'
    assert '旧课标' in editions['sujiao']['name']
    items = data['items']
    for edition_id, edition in editions.items():
        placements = [p for x in items for p in x['textbook_editions'] if p['id'] == edition_id]
        assert edition['count'] == len(placements) > 0
        assert set(edition['books']) == {b for p in placements for b in p['books']}
    chibi = next(x for x in items if x['title'].startswith('赤壁赋'))
    assert {'id': 'sujiao', 'books': ['必修一']} in chibi['textbook_editions']
    assert any(p['id']=='renjiao' for p in chibi['textbook_editions'])
    assert all(not x['textbook_editions'] for x in items if x['collection']=='公开真题材料')
    assert all(x['books']==next(p['books'] for p in x['textbook_editions'] if p['id']=='renjiao') for x in items if x['books'])
