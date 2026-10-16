from test_catalog import teacher_client


def test_knowledge_first_and_optional_article_find_questions_across_materials(teacher_client):
    c=teacher_client
    initial=c.get('/api/question-library').json()
    assert initial['total']==0 and any(k['id']=='tag-parallel' for k in initial['knowledge'])
    article=next(a for a in initial['articles'] if a['title']=='登高')
    linked=c.get('/api/question-library',params={'article':article['id'],'limit':50}).json()
    assert {k['id'] for k in linked['knowledge']}=={k['id'] for k in article['knowledge']}
    assert linked['total']>0
    keys={k['id'] for k in linked['knowledge']}
    assert all(any(k['id'] in keys for k in q['knowledge']) for q in linked['items'])
    direct=c.get('/api/question-library?knowledge_id=tag-parallel').json()
    assert direct['total']==4
    assert len({q['article']['id'] for q in direct['items']})>1
    assert all(any(k['id']=='tag-parallel' for k in q['knowledge']) for q in direct['items'])
    assert c.get('/api/question-library?knowledge_id=tag-parallel&level=基础').json()['total']==1
    first=c.get('/api/question-library?knowledge_id=tag-parallel&limit=1').json()
    second=c.get('/api/question-library?knowledge_id=tag-parallel&limit=1&offset=1').json()
    assert first['items'][0]['id']!=second['items'][0]['id']
    assert c.get('/api/question-library',params={'knowledge_id':'tag-parallel','q':'不存在的题干'}).json()['total']==0
    combined=c.get('/api/question-library',params={'article':article['id'],'knowledge_id':'tag-parallel'}).json()
    assert combined['total']==direct['total']
    assert all(any(k['id']=='tag-parallel' for k in q['knowledge']) for q in combined['items'])
    assert any(q['article']['id']!=article['id'] for q in combined['items'])
    assert c.get('/api/question-library',params={'article':article['id'],'knowledge_id':'tag-parallel','level':'基础'}).json()['total']==1
    assert c.get('/api/question-library',params={'article':article['id'],'q':'不会出现的字符串'}).json()['total']==0
    one=c.get('/api/question-library',params={'article':article['id'],'limit':1}).json()
    two=c.get('/api/question-library',params={'article':article['id'],'limit':1,'offset':1}).json()
    assert one['items'][0]['id']!=two['items'][0]['id']
    unrelated=next(k['id'] for k in c.get('/api/question-links/knowledge?limit=50').json()['items'] if k['id'] not in keys)
    assert c.get('/api/question-library',params={'article':article['id'],'knowledge_id':unrelated}).status_code==422
    assert c.get('/api/workspace').json()['points']==[]
    for query,code in [('article=missing',404),('knowledge_id=missing',404),('offset=-1',422),('level=invalid',422)]:
        assert c.get('/api/question-library?'+query).status_code==code
    c.post('/api/logout');assert c.get('/api/question-library').status_code==401


def test_unified_library_facets_and_question_selection_keep_account_isolation(teacher_client):
    c=teacher_client
    article=c.post('/api/articles',json={'title':'私人筛选文章','genre':'阅读','content':'私有题库材料，别人看不到。'}).json()['id']
    point=c.post('/api/points',json={'article_id':article,'name':'校本独有知识点'}).json()['id']
    q=c.post('/api/questions',json={'point_id':point,'level':'基础','material':'私有题库材料，别人看不到。','prompt':'私人筛选题目','reference':'私人答案','rubric':'私人标准','max_score':10}).json()['id']
    article_key=c.get('/api/question-links/articles?q=私人筛选文章').json()['items'][0]['id']
    mine=c.get('/api/question-library',params={'article':article_key,'q':'私人筛选题目'}).json();assert mine['total']==1
    article_key=mine['items'][0]['article']['id'];category=mine['items'][0]['knowledge'][0]['id']
    assert c.get('/api/question-library',params={'knowledge_id':category,'q':'私人筛选题目'}).json()['total']==1
    assert c.post('/api/register',json={'username':'library_b','password':'independent-password-123'}).status_code==200
    other=c.get('/api/question-library').json()
    assert all(a['id']!=article_key for a in other['articles']) and all(k['id']!=category for k in other['knowledge'])
    assert c.get('/api/question-library?q=私人筛选题目').json()['total']==0
    assert c.get('/api/question-library?article='+article_key).status_code==404
    assert c.get('/api/question-library?knowledge_id='+category).status_code==404
    assert c.get('/api/question-links/questions/teaching:'+str(q)).status_code==404
