from test_catalog import teacher_client


def test_unified_library_intersects_article_topic_level_and_search(teacher_client):
    c=teacher_client
    initial=c.get('/api/question-library').json()
    assert initial['total']==186 and len(initial['items'])==10
    article=next(a for a in initial['articles'] if a['title']=='登高')['id']
    article_rows=c.get('/api/question-library',params={'article':article}).json()
    assert article_rows['total']==9
    assert all(q['article']['id']==article for q in article_rows['items'])
    assert c.get('/api/question-library?knowledge_id=tag-parallel').json()['total']==4
    combined=c.get('/api/question-library',params={'article':article,'knowledge_id':'tag-parallel'}).json()
    assert combined['total']==3
    assert all(any(k['id']=='tag-parallel' for k in q['knowledge']) for q in combined['items'])
    single=c.get('/api/question-library',params={'article':article,'knowledge_id':'tag-parallel','level':'基础'}).json()
    assert single['total']==1
    assert c.get('/api/question-library',params={'article':article,'knowledge_id':'tag-parallel','q':'不会出现的字符串'}).json()['total']==0
    assert c.get('/api/question-library',params={'article':article,'q':'杜甫'}).json()['total']==9
    page2=c.get('/api/question-library?offset=10').json()
    assert not {q['id'] for q in initial['items']}&{q['id'] for q in page2['items']}
    assert all('reference' not in q and 'material' not in q for q in initial['items'])
    assert c.get('/api/workspace').json()['points']==[]
    for query,code in [('article=missing',404),('knowledge_id=missing',404),('offset=-1',422),('limit=1000',422),('level=invalid',422)]:
        assert c.get('/api/question-library?'+query).status_code==code
    c.post('/api/logout');assert c.get('/api/question-library').status_code==401


def test_unified_library_facets_and_question_selection_keep_account_isolation(teacher_client):
    c=teacher_client
    article=c.post('/api/articles',json={'title':'私人筛选文章','genre':'阅读','content':'私有题库材料，别人看不到。'}).json()['id']
    point=c.post('/api/points',json={'article_id':article,'name':'校本独有知识点'}).json()['id']
    q=c.post('/api/questions',json={'point_id':point,'level':'基础','material':'私有题库材料，别人看不到。','prompt':'私人筛选题目','reference':'私人答案','rubric':'私人标准','max_score':10}).json()['id']
    mine=c.get('/api/question-library?q=私人筛选题目').json();assert mine['total']==1
    article_key=mine['items'][0]['article']['id'];category=mine['items'][0]['knowledge'][0]['id']
    assert c.post('/api/register',json={'username':'library_b','password':'independent-password-123'}).status_code==200
    other=c.get('/api/question-library').json()
    assert all(a['id']!=article_key for a in other['articles']) and all(k['id']!=category for k in other['knowledge'])
    assert c.get('/api/question-library?q=私人筛选题目').json()['total']==0
    assert c.get('/api/question-library?article='+article_key).status_code==404
    assert c.get('/api/question-library?knowledge_id='+category).status_code==404
    assert c.get('/api/question-links/questions/teaching:'+str(q)).status_code==404
