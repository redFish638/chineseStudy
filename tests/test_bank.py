import json

from backend import bank
from test_catalog import teacher_client


def make_point(client, name='意象与悲秋意境'):
    article_id=client.post('/api/catalog/deng-gao/open').json()['id']
    point_id=client.post('/api/points',json={'article_id':article_id,'name':name,'description':'结合原文训练'}).json()['id']
    return article_id,point_id


def test_bank_sources_paging_and_filters(teacher_client):
    c=teacher_client
    result=c.get('/api/bank?limit=10').json()
    assert result['stats']['materials']==len(bank.seed_records())
    assert result['stats']['sources']['gaokao']==111
    assert result['stats']['sources']['mock']==0
    assert result['stats']['questions']==186
    page2=c.get('/api/bank?limit=10&offset=10').json()
    assert not ({x['id'] for x in result['items']}&{x['id'] for x in page2['items']})
    assert c.get('/api/bank?source_type=mock').json()['total']==0
    novels=c.get('/api/bank?genre=阅读&source_type=gaokao&has_questions=true').json()
    assert novels['total']==53
    assert all(x['genre']=='阅读' and x['question_count'] for x in novels['items'])
    assert c.get('/api/bank?tag=not-a-tag').status_code==422
    assert c.get('/api/bank?offset=-1').status_code==422
    assert c.get('/api/bank?limit=1000').status_code==422
    c.post('/api/logout')
    assert c.get('/api/bank').status_code==401
    assert c.get('/api/bank/materials/curated:deng-gao').status_code==401


def test_points_get_different_materials_automatically_with_verifiable_evidence(teacher_client):
    c=teacher_client
    article_id,point_id=make_point(c)
    result=c.get(f'/api/points/{point_id}/related-materials?limit=50').json()
    assert result['total']>20
    assert result['query_tags']
    assert all(x['title']!='登高' and x['id']!='curated:deng-gao' for x in result['items'])
    hashes=[]
    for item in result['items'][:6]:
        detail=c.get('/api/bank/materials/'+item['id']).json()
        hashes.append(detail['content_hash'])
        assert set(item['match_tags'])&set(detail['tags'])
        if item['match_evidence']: assert item['match_evidence'] in detail['body']
    assert len(hashes)==len(set(hashes))
    inline=c.get(f'/api/articles/{article_id}/related-materials').json()['items']
    assert inline[0]['point_id']==point_id and len(inline[0]['items'])==3
    _,unknown=make_point(c,'未定义知识ABC')
    assert c.get(f'/api/points/{unknown}/related-materials').json()['total']==0


def test_synonyms_methods_and_duplicate_work_exclusion():
    records=bank.seed_records()
    original=next(x for x in records if x['id']=='curated:he-tang-yue-se')
    query,results=bank.recommend(records,'通感的作用','',original['body'],original['title'],'阅读')
    assert query==['synesthesia'] and results
    assert all('synesthesia' in r['match_tags'] for r in results)
    assert all('he-tang-yue-se' not in r['id'] for r in results)
    a=next(x for x in records if x['id']=='curated:deng-gao')
    duplicate={**a,'id':'another-edition','body':a['body'].replace('，',' ')}
    assert bank.same_work(duplicate,a['body'],a['title'])
    assert not bank.same_work({**duplicate,'title':'文言文阅读','body':'这是另一篇完全不同的文言材料，讲述的是第二位人物。'},'此篇古代材料写的是第一位人物的事迹。','文言文阅读')
    # A matching theme alone cannot satisfy the specific method "通感".
    _,none=bank.recommend([{**duplicate,'tags':['imagery']}],'通感','',original['body'],original['title'],'阅读')
    assert none==[]


def test_batch_import_is_persistent_idempotent_and_mock_source_is_transparent(teacher_client):
    c=teacher_client
    article_id,point_id=make_point(c,'人物形象')
    body={'materials':[{'title':'校本模拟阅读A','author':'教师自编','genre':'阅读','source_type':'mock',
        'source_label':'校本2026模拟，教师提供','year':'2026','region':'校本','body':'父亲冒雨走进教室，轻轻放下修好的书包，又默默转身离开。',
        'tags':['character','detail'],'questions':[{'prompt':'结合动作描写分析父亲的形象。','reference':'体贴细致。','analysis':'举出动作并解释品质。','max_score':6,'level':'基础'}]}]}
    first=c.post('/api/bank/import',json=body)
    assert first.status_code==200 and first.json()=={'created':1,'merged':0,'questions_added':1}
    assert c.post('/api/bank/import',json=body).json()=={'created':0,'merged':1,'questions_added':0}
    rows=c.get('/api/bank?source_type=mock').json()
    assert rows['total']==1 and '未外部核验' in rows['items'][0]['review']
    related=c.get(f'/api/points/{point_id}/related-materials?source_type=mock').json()
    assert related['total']==1
    id=related['items'][0]['id']
    detail=c.get('/api/bank/materials/'+id).json()
    assert detail['questions'][0]['reference']=='体贴细致。'
    # Seeding another release never overwrites teacher imports or teaching records.
    from backend.main import DB,seed_material_bank
    with DB() as db: seed_material_bank(db);db.commit()
    assert c.get('/api/bank/materials/'+id).json()['body']==body['materials'][0]['body']
    assert c.get('/api/workspace').json()['points'][0]['id']==point_id
    invalid={'materials':[{**body['materials'][0],'tags':['invented-tag']} ]}
    assert c.post('/api/bank/import',json=invalid).status_code==422


def test_selecting_other_material_preserves_original_target_and_original_answer(teacher_client):
    c=teacher_client
    _,point_id=make_point(c,'思想情感')
    result=c.get(f'/api/points/{point_id}/related-materials?source_type=gaokao&has_questions=true').json()
    chosen=result['items'][0]
    detail=c.get('/api/bank/materials/'+chosen['id']).json()
    question=detail['questions'][0]
    saved=c.post('/api/questions',json={'point_id':point_id,'level':'巩固','material':detail['body'],
        'prompt':question['prompt'],'reference':question['reference'],'rubric':question['analysis'],'max_score':question['max_score']})
    assert saved.status_code==200
    q=c.get('/api/workspace').json()['questions'][0]
    assert q['point_id']==point_id and q['reference']==question['reference'].strip()
    assert c.post('/api/bank/materials/'+chosen['id']+'/open').status_code==200


def test_existing_database_gets_additive_bank_tables_without_losing_teaching_data(tmp_path):
    from sqlalchemy import create_engine,select,func
    from sqlalchemy.orm import Session
    from backend.main import Base,Admin,Article,Point,BankMaterial,seed_material_bank
    engine=create_engine('sqlite:///'+str(tmp_path/'existing-production-copy.db'))
    original_tables=[table for table in Base.metadata.sorted_tables if not table.name.startswith('zhiyu_bank_')]
    Base.metadata.create_all(engine,tables=original_tables)
    with Session(engine) as db:
        db.add(Admin(username='existing-teacher',password_hash='existing-password-hash'))
        a=Article(title='原有教学文章',genre='阅读',content='用户已有正文，不得重置。');db.add(a);db.flush()
        db.add(Point(article_id=a.id,name='原有知识点',description='原有目标'));db.commit()
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_material_bank(db);db.commit()
        assert db.scalar(select(Admin)).password_hash=='existing-password-hash'
        assert db.scalar(select(Article)).content=='用户已有正文，不得重置。'
        assert db.scalar(select(Point)).name=='原有知识点'
        assert db.scalar(select(func.count()).select_from(BankMaterial))==len(bank.seed_records())
        seed_material_bank(db);db.commit()
        assert db.scalar(select(func.count()).select_from(BankMaterial))==len(bank.seed_records())
    engine.dispose()
