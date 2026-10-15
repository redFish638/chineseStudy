import hashlib
import time

from sqlalchemy import Column, MetaData, Table, create_engine, inspect, select
from sqlalchemy.orm import Session

from test_workflow import client, login


def test_accounts_cannot_read_or_mutate_each_others_teaching_graph(client):
    c=client;login(c)
    a=c.post('/api/articles',json={'title':'A的秘密文章','author':'私人作者','genre':'阅读','content':'私有文章中有一盏灯。'}).json()['id']
    p=c.post('/api/points',json={'article_id':a,'name':'象征','description':'A的私人说明'}).json()['id']
    question={'point_id':p,'level':'基础','material':'A的私有训练材料','prompt':'A的题目','reference':'A的答案','rubric':'A的评分','max_score':10}
    q=c.post('/api/questions',json=question).json()['id']
    assignment=c.post('/api/assignments',json={'question_id':q,'student':'私人学生'}).json()
    c.post('/api/tasks/'+assignment['token']+'/submit',json={'answer':'私人作答'})
    submission=c.get('/api/workspace').json()['submissions'][0]['id']
    shared_a=c.post('/api/catalog/deng-gao/open').json()['id']
    analysis=c.post(f'/api/articles/{shared_a}/analyze',json={}).json()
    confirmation={k:analysis[k] for k in ['article_digest','source','points']}
    c.post(f'/api/articles/{shared_a}/confirm-analysis',json=confirmation)
    cookies=dict(c.cookies)
    assert c.post('/api/register',json={'username':'user_b','password':'separate-password-4827'}).status_code==200
    assert c.get('/api/workspace').json()=={'user':{'username':'user_b'},'articles':[],'points':[],'questions':[],'assignments':[],'submissions':[]}
    assert c.get('/api/knowledge-library').json()['total']==0
    assert 'A的秘密文章' not in c.get('/api/question-links/articles').text
    assert c.get(f'/api/question-links/questions/teaching:{q}').status_code==404
    for path in [f'/api/articles/{a}/related-materials',f'/api/points/{p}/related-materials',f'/api/points/{p}/practice-candidates']:
        assert c.get(path).status_code==404
    assert c.put(f'/api/articles/{a}',json={'title':'篡改','genre':'阅读','content':'篡改内容'}).status_code==404
    assert c.post('/api/points',json={'article_id':a,'name':'越权'}).status_code==404
    assert c.put(f'/api/points/{p}',json={'article_id':a,'name':'越权'}).status_code==404
    assert c.post(f'/api/articles/{shared_a}/confirm-analysis',json=confirmation).status_code==404
    assert c.post(f'/api/articles/{a}/analyze',json={}).status_code==404
    assert c.put(f'/api/questions/{q}',json=question).status_code==404
    assert c.post('/api/questions',json=question).status_code==404
    assert c.post('/api/assignments',json={'question_id':q,'student':'越权'}).status_code==404
    assert c.put(f'/api/submissions/{submission}/review',json={'score':5,'feedback':'越权','issue':'越权'}).status_code==404
    shared_b=c.post('/api/catalog/deng-gao/open').json()['id'];assert shared_b!=shared_a
    own=c.post('/api/articles',json={'title':'B的文章','genre':'阅读','content':'B的私人内容'}).json()['id']
    assert c.post('/api/points',json={'article_id':own,'name':'比喻','description':'B的说明'}).status_code==200
    assert c.put(f'/api/points/{p}',json={'article_id':own,'name':'挪用'}).status_code==404
    c.cookies.clear();c.cookies.update(cookies)
    assert len(c.get('/api/workspace').json()['points'])==len(confirmation['points'])+1
    assert c.put(f'/api/articles/{own}',json={'title':'越权','genre':'阅读','content':'越权'}).status_code==404
    assert c.get('/api/tasks/'+assignment['token']).status_code==200  # bearer task links remain valid


def test_imported_bank_is_private_and_seed_bank_is_shared(client):
    c=client;login(c)
    item={'title':'A的学校卷','author':'校本','genre':'阅读','source_type':'mock','source_label':'校内私有','body':'独有的私有材料原文','tags':['symbol'],'questions':[{'prompt':'私有题','reference':'私有答案'}]}
    assert c.post('/api/bank/import',json={'materials':[item]}).status_code==200
    detail=c.get('/api/bank?q=A的学校卷').json()['items'][0];key=detail['id']
    assert c.post('/api/register',json={'username':'bank_user','password':'another-password-8224'}).status_code==200
    assert c.get('/api/bank?q=A的学校卷').json()['total']==0
    assert c.get('/api/bank/materials/'+key).status_code==404
    assert c.post('/api/bank/materials/'+key+'/open').status_code==404
    assert c.get('/api/catalog').json()['bank_materials']==576
    assert c.get('/api/bank?source_type=textbook').status_code==200
    assert c.post('/api/bank/import',json={'materials':[item]}).json()['created']==1
    assert c.get('/api/bank?q=A的学校卷').json()['items'][0]['id']!=key


def test_additive_legacy_migration_relogin_and_repeated_start_are_safe(client,tmp_path,monkeypatch):
    import backend.main as m
    legacy=create_engine('sqlite:///'+str(tmp_path/'legacy.db'));metadata=MetaData()
    for model in [m.Admin,m.Article,m.BankMaterial,m.LoginSession]:
        Table(model.__tablename__,metadata,*[Column(col.name,col.type,primary_key=col.primary_key,nullable=col.nullable)
            for col in model.__table__.columns if col.name not in {'owner_id','admin_id','author'} or (model is m.BankMaterial and col.name=='author')])
    metadata.create_all(legacy)
    with legacy.begin() as con:
        con.execute(metadata.tables['zhiyu_admins'].insert(),[{'id':1,'username':'teacher','password_hash':m.digest('legacy-password-123')},{'id':2,'username':'other','password_hash':m.digest('other-password-123')}])
        con.execute(metadata.tables['zhiyu_articles'].insert(),{'id':7,'title':'旧文章','genre':'阅读','content':'原数据正文'})
        con.execute(metadata.tables['zhiyu_login_sessions'].insert(),{'token':hashlib.sha256(b'old-cookie').hexdigest(),'expires':int(time.time())+1000})
    monkeypatch.setattr(m,'engine',legacy)
    m.migrate_ownership_columns();m.migrate_ownership_columns()
    with Session(legacy) as db:
        m.adopt_legacy_records(db);db.commit();m.adopt_legacy_records(db);db.commit()
        article=db.get(m.Article,7)
        assert article.owner_id==1 and article.content=='原数据正文' and article.author==''
        assert not list(db.scalars(select(m.LoginSession)))
    assert {'owner_id','author'}<={x['name'] for x in inspect(legacy).get_columns('zhiyu_articles')}
    legacy.dispose()


def test_register_password_validation_duplicate_and_current_identity(client):
    c=client
    assert c.post('/api/register',json={'username':'new_teacher','password':'short'}).status_code==422
    assert c.post('/api/register',json={'username':'new_teacher','password':'a-long-password-123'}).status_code==200
    assert c.get('/api/workspace').json()['user']['username']=='new_teacher'
    assert c.post('/api/register',json={'username':'new_teacher','password':'a-long-password-123'}).status_code==409
    c.post('/api/logout');assert c.get('/api/workspace').status_code==401
    assert c.post('/api/login',json={'username':'new_teacher','password':'a-long-password-123'}).status_code==200
    assert c.post('/api/articles',json={'title':'过长','genre':'阅读','content':'字'*22000}).status_code==422
