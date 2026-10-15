from test_catalog import teacher_client


def add_article(c,title):
    return c.post('/api/articles',json={'title':title,'genre':'诗歌','content':'月出惊山鸟，时鸣春涧中。'}).json()['id']


def test_preview_not_indexed_confirmation_indexes_and_survives_new_requests(teacher_client):
    c=teacher_client
    assert c.get('/api/knowledge-library').json()['stats']=={'knowledge_points':0,'confirmed_records':0,'articles':0}
    article=c.post('/api/catalog/deng-gao/open').json()['id']
    preview=c.post(f'/api/articles/{article}/analyze',json={}).json()
    assert c.get('/api/knowledge-library').json()['total']==0
    body={k:preview[k] for k in ['source','article_digest','points']}
    assert c.post(f'/api/articles/{article}/confirm-analysis',json=body).json()['created']==3
    library=c.get('/api/knowledge-library').json()
    assert library['stats']=={'knowledge_points':3,'confirmed_records':3,'articles':1}
    selected=library['items'][0]
    detail=c.get('/api/knowledge-library/'+selected['id']).json()
    assert detail['articles'][0]['id']==article
    assert '原文依据：' in detail['articles'][0]['points'][0]['description']
    assert c.post(f'/api/articles/{article}/confirm-analysis',json=body).json()['created']==0
    assert c.get('/api/knowledge-library').json()['stats']==library['stats']
    c.post('/api/logout')
    assert c.get('/api/knowledge-library').status_code==401
    assert c.get('/api/knowledge-library/'+selected['id']).status_code==401
    c.post('/api/login',json={'username':'teacher','password':'test-only-password-9843'})
    assert c.get('/api/knowledge-library/'+selected['id']).json()==detail


def test_same_name_groups_without_losing_article_specific_evidence_and_training(teacher_client):
    c=teacher_client
    a=add_article(c,'第一首');b=add_article(c,'第二首')
    ids=[]
    for article,description,name in [(a,'第一篇的独立依据与目标','意象与意境'),(b,'第二篇的独立依据与目标','意象与意境')]:
        ids.append(c.post('/api/points',json={'article_id':article,'name':name,'description':description}).json()['id'])
    c.post('/api/questions',json={'point_id':ids[0],'level':'基础','material':'原文','prompt':'解释景物','reference':'原句依据','rubric':'依据信息','max_score':5})
    result=c.get('/api/knowledge-library').json()
    assert result['stats']=={'knowledge_points':1,'confirmed_records':2,'articles':2}
    item=result['items'][0]
    assert item['article_count']==2 and item['question_count']==1
    detail=c.get('/api/knowledge-library/'+item['id']).json()
    assert {p['description'] for a in detail['articles'] for p in a['points']}=={'第一篇的独立依据与目标','第二篇的独立依据与目标'}
    assert {p['id'] for a in detail['articles'] for p in a['points']}==set(ids)
    assert c.get('/api/knowledge-library?q=第二首').json()['total']==1
    assert c.get('/api/knowledge-library?q=独立依据').json()['total']==1
    assert c.get('/api/knowledge-library?genre=文言文').json()['total']==0
    assert c.get('/api/knowledge-library?q=不存在').json()['total']==0
    c.put('/api/points/'+str(ids[1]),json={'article_id':b,'name':'声音描写','description':'修改后的目标'})
    assert c.get('/api/knowledge-library').json()['total']==2
    assert c.get('/api/knowledge-library/'+item['id']).json()['article_count']==1
    c.put('/api/points/'+str(ids[0]),json={'article_id':a,'name':'声音描写','description':'另一篇目标'})
    assert c.get('/api/knowledge-library/'+item['id']).status_code==404
    assert c.get('/api/knowledge-library').json()['total']==1


def test_pagination_input_validation_and_no_semantic_overmerge(teacher_client):
    c=teacher_client;a=add_article(c,'校本文章')
    for i in range(22):c.post('/api/points',json={'article_id':a,'name':'知识点'+str(i),'description':''})
    first=c.get('/api/knowledge-library?limit=20').json();second=c.get('/api/knowledge-library?limit=20&offset=20').json()
    assert first['total']==22 and len(first['items'])==20 and len(second['items'])==2
    assert not {x['id'] for x in first['items']}&{x['id'] for x in second['items']}
    for query in ['limit=0','limit=51','offset=-1','genre=错误文体','q='+'字'*201]:
        assert c.get('/api/knowledge-library?'+query).status_code==422
    assert c.get('/api/knowledge-library/missing').status_code==404
    for name in ['比喻','比喻论证']:
        c.post('/api/points',json={'article_id':a,'name':name,'description':''})
    assert c.get('/api/knowledge-library?q=比喻').json()['total']==2
