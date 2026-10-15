import re
from backend import bank, catalog
from backend.poetry_text import BODIES, exam_poetry
from test_catalog import teacher_client


def test_all_exam_poems_have_only_verse_and_keep_source_questions():
    records={r['id']:r for r in bank.seed_records()}
    assert len(BODIES)==29
    for raw in catalog.EXAM_RECORDS:
        i=str(raw['index']);body,prompt=exam_poetry(raw)
        entry=catalog.get_entry('gaokao-poetry-'+i)
        record=records['gaokao:poetry:'+i]
        assert body==entry['content']==record['body']
        assert len(body)>45
        assert not re.search(r'阅读下面|完成|【注|\[注\]|①|（1）|14\.',body)
        assert not prompt.startswith('阅读')
        assert '（1）' in prompt or '(1)' in prompt or re.search(r'(?:^|\n)\s*\d+[.．、]',prompt)
        for heading in entry['title'].split(' / ')+entry['author'].split(' / '):
            assert heading not in body
        assert all(p['evidence'] in body for p in entry['points'])
    expected='满眼长江水，苍然何郡山？\n向来万里意，今在一窗间。\n众木俱含晚，孤云遂不还。\n此中有佳句，吟断不相关。'
    assert BODIES['18']==expected
    assert '许道宁：北宋画家' in records['gaokao:poetry:18']['questions'][0]['prompt']
    assert '（1）诗的颈联' in records['gaokao:poetry:11']['questions'][0]['prompt']
    assert '内宴奉诏作' not in records['gaokao:poetry:11']['questions'][0]['prompt']
    assert '平生不受等闲思。' in BODIES['19']
    assert '\n\n' in BODIES['6'] and '\n\n' in BODIES['28']
    assert all('legacy_content' not in item for item in catalog.listing())


def test_existing_adopted_poems_are_repaired_without_losing_points(teacher_client):
    import backend.main as m
    c=teacher_client;entry=catalog.get_entry('gaokao-poetry-18')
    old=entry['legacy_content']
    a=c.post('/api/articles',json={'title':entry['title'],'author':entry['author'],'genre':'诗歌','content':old}).json()['id']
    custom=c.post('/api/articles',json={'title':entry['title'],'genre':'诗歌','content':old+'\n我的批注'}).json()['id']
    p=c.post('/api/points',json={'article_id':a,'name':'意象','description':'我的研读记录'}).json()['id']
    with m.DB() as db:
        m.repair_poetry_bodies(db);db.commit()
        m.repair_poetry_bodies(db);db.commit()
    workspace=c.get('/api/workspace').json()
    assert next(x for x in workspace['articles'] if x['id']==a)['content']==entry['content']
    assert next(x for x in workspace['articles'] if x['id']==custom)['content']==old+'\n我的批注'
    assert next(x for x in workspace['points'] if x['id']==p)['description']=='我的研读记录'
    c.post('/api/register',json={'username':'poetry-other','password':'independent-poetry-password'})
    assert c.get('/api/workspace').json()['articles']==[]
