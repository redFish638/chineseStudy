from backend import bank,catalog
from test_catalog import teacher_client


def test_poetry_titles_and_byline_match_across_catalog_and_bank():
    records={x['id']:x for x in bank.seed_records()}
    for index in range(29):
        entry=catalog.get_entry('gaokao-poetry-'+str(index));row=records['gaokao:poetry:'+str(index)]
        assert (entry['title'],entry['author'])==(row['title'],row['author'])
        assert '古代诗歌阅读' not in entry['title'] and not entry['title'].startswith(entry['exam_year']+'年')
        assert row['author'] not in {'见材料署名','署名待核对'}
    assert records['gaokao:poetry:9']['title']=='金陵望汉江'
    assert records['gaokao:poetry:9']['author']=='李白'
    assert records['gaokao:poetry:9']['year']=='2016'
    assert records['gaokao:poetry:6']['author']=='韦庄 / 郭震'
    assert records['gaokao:literary:11']['title']=='玻璃'
    assert records['gaokao:literary:11']['author']=='贾平凹'
    assert records['gaokao:classical:20']['title']=='史记·孙子吴起列传（节选）'
    assert records['gaokao:classical:20']['author']=='司马迁'


def test_legacy_exam_metadata_repair_preserves_private_points_questions_and_custom_titles(teacher_client):
    import backend.main as m
    c=teacher_client;entry=catalog.get_entry('gaokao-poetry-9')
    a=c.post('/api/articles',json={'title':entry['legacy_title'],'genre':'诗歌','content':entry['content']}).json()['id']
    custom=c.post('/api/articles',json={'title':'我自定的课堂标题','genre':'诗歌','content':entry['content']}).json()['id']
    point=c.post('/api/points',json={'article_id':a,'name':'意象与意境','description':'保留我的个人解析'}).json()['id']
    with m.DB() as db:
        m.repair_legacy_exam_titles(db);db.commit();m.repair_legacy_exam_titles(db);db.commit()
    data=c.get('/api/workspace').json()
    article=next(x for x in data['articles'] if x['id']==a)
    assert article['title']=='金陵望汉江' and article['author']=='李白'
    assert next(x for x in data['articles'] if x['id']==custom)['title']=='我自定的课堂标题'
    assert next(x for x in data['points'] if x['id']==point)['description']=='保留我的个人解析'
    selected=c.get('/api/question-links/articles?q=金陵望汉江').json()['items']
    assert selected and all(x['title']=='金陵望汉江' and x['author']=='李白' for x in selected)
    assert c.get('/api/catalog').json()['items'][0]
