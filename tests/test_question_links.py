from copy import deepcopy

from backend import bank, question_links
from test_catalog import teacher_client


def test_all_existing_questions_have_two_link_dimensions_without_mutating_source():
    records=bank.seed_records();before=deepcopy(records)
    index=question_links.build(records,[],[],[],{})
    assert records==before
    assert index['stats']['questions']==index['stats']['bank_questions']==270
    assert index['stats']['teaching_questions']==0
    assert len(index['articles'])<len(records)  # Same-body reading editions merge, questions never disappear.
    assert 'unclassified' not in index['knowledge']
    for key,q in index['questions'].items():
        article=index['articles'][q['article']['id']]
        assert key in article['question_ids'] and q['knowledge']
        for category in q['knowledge']:
            assert key in index['knowledge'][category['id']]['question_ids']
            assert category['id'] in article['categories']
    parallel=index['knowledge']['tag-parallel']
    assert len(parallel['question_ids'])==4
    assert all('gaokao:classical:' not in key for key in parallel['question_ids'])


def test_article_knowledge_question_round_trip_and_pagination(teacher_client):
    c=teacher_client
    result=c.get('/api/question-links/articles?q=登高').json()
    assert result['stats']['questions']==270 and result['total']==1
    article=result['items'][0]
    detail=c.get('/api/question-links/articles/'+article['id']).json()
    assert detail['title']=='登高' and detail['question_count']==9
    parallel=next(k for k in detail['knowledge'] if k['id']=='tag-parallel')
    assert parallel['question_count']==3
    category=c.get('/api/question-links/knowledge/tag-parallel').json()
    assert category['question_count']==4 and category['article_count']>=10
    assert len(category['articles'])==10
    assert all(any(k['id']=='tag-parallel' for k in q['knowledge']) for q in category['questions'])
    first=c.get('/api/question-links/articles/'+article['id']+'?limit=1').json()
    second=c.get('/api/question-links/articles/'+article['id']+'?limit=1&offset=1').json()
    assert first['questions'][0]['id']!=second['questions'][0]['id']
    q=c.get('/api/question-links/questions/'+first['questions'][0]['id']).json()
    assert q['article']['id']==article['id'] and q['reference'] and q['knowledge']
    assert q['id'] in [r['id'] for r in detail['questions']]
    assert c.get('/api/question-links/knowledge?q=对偶').json()['items'][0]['id']=='tag-parallel'
    next_articles=c.get('/api/question-links/knowledge/tag-parallel?article_offset=10').json()['articles']
    assert next_articles and not {a['id'] for a in next_articles}&{a['id'] for a in category['articles']}
    for view in ['articles','knowledge']:
        only=c.get('/api/question-links/'+view+'?has_questions=true&limit=50').json()
        assert all(item['question_count'] for item in only['items'])
    # All tags and questions were read, never confirmed as teacher knowledge points.
    assert c.get('/api/workspace').json()['points']==[]


def test_training_material_can_differ_from_goal_article_and_existing_tasks_stay_intact(teacher_client):
    c=teacher_client
    owner=c.post('/api/catalog/deng-gao/open').json()['id']
    point=c.post('/api/points',json={'article_id':owner,'name':'意象与意境','description':'教师确认的学习目标'}).json()['id']
    bird=next(x for x in c.get('/api/catalog').json()['items'] if x['id']=='niao-ming-jian')
    question=c.post('/api/questions',json={'point_id':point,'level':'巩固','material':bird['content'],'prompt':'结合本诗的景物分析意境。',
        'reference':'先写景物，再说明意境','rubric':'原句与分析各五分','max_score':10}).json()['id']
    assignment=c.post('/api/assignments',json={'question_id':question,'student':'三维索引验收'}).json()
    assert c.post('/api/tasks/'+assignment['token']+'/submit',json={'answer':'山中月出，鸟声映衬宁静。'}).status_code==200
    before=c.get('/api/workspace').json()
    q=c.get('/api/question-links/questions/teaching:'+str(question)).json()
    assert q['article']['title']=='鸟鸣涧' and q['goal_article']['title']=='登高'
    assert q['knowledge']==[{'id':'tag-imagery','name':'意象与意境','tag':'imagery'}]
    assert q['assignment_count']==1
    reading=c.get('/api/question-links/articles/'+q['article']['id']).json()
    assert 'teaching:'+str(question) in [x['id'] for x in reading['questions']]
    imagery=c.get('/api/question-links/knowledge/tag-imagery?limit=50').json()
    assert q['id'] in [x['id'] for x in imagery['questions']]
    assert c.get('/api/workspace').json()==before
    # Unknown reading stays explicit; it must not be mislabeled as the goal article.
    unknown=c.post('/api/questions',json={'point_id':point,'level':'基础','material':'这是一份校本新编的独立材料，尚未提供文章篇名和作者。',
        'prompt':'概括画面','reference':'依据原文','rubric':'准确完整','max_score':5}).json()['id']
    other=c.get('/api/question-links/questions/teaching:'+str(unknown)).json()
    assert other['article']['title'].startswith('自定义训练材料')
    assert '不推断' in other['article_basis'] and other['goal_article']['title']=='登高'
    # Editing a learning objective updates live labels, leaving the distributed question intact.
    c.put('/api/points/'+str(point),json={'article_id':owner,'name':'比喻','description':'修订后的教学目标'})
    updated=c.get('/api/question-links/questions/teaching:'+str(question)).json()
    assert updated['knowledge'][0]['id']=='tag-metaphor'
    assert updated['article']==q['article'] and updated['assignment_count']==1
    assert c.get('/api/tasks/'+assignment['token']).json()['submission']['answer']=='山中月出，鸟声映衬宁静。'


def test_index_validation_and_teacher_only_access(teacher_client):
    c=teacher_client
    for suffix in ['limit=0','limit=51','offset=-1','q='+'字'*201]:
        assert c.get('/api/question-links/articles?'+suffix).status_code==422
    article=c.get('/api/question-links/articles?limit=1').json()['items'][0]['id']
    for path in ['/api/question-links/nope','/api/question-links/articles/missing','/api/question-links/knowledge/missing','/api/question-links/questions/missing']:
        assert c.get(path).status_code==404
    assert c.get('/api/question-links/knowledge/tag-parallel?article_offset=-1').status_code==422
    paths=['/api/question-links/articles','/api/question-links/knowledge','/api/question-links/articles/'+article,
           '/api/question-links/knowledge/tag-parallel','/api/question-links/questions/bank:curated:deng-gao:0:基础']
    c.post('/api/logout')
    for path in paths: assert c.get(path).status_code==401
