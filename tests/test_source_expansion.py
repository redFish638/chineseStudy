import json
from pathlib import Path
import re

from backend import analysis, bank, catalog
from backend.public_expansion import READINGS,MODERN
from test_catalog import teacher_client


def test_original_readings_are_deduplicated_and_not_mislabelled_as_exam_questions():
    original=[r for r in bank.seed_records() if not r['id'].startswith('expanded:')]
    hashes={bank.body_hash(r['body']) for r in original}
    assert len(READINGS)==741
    assert sum(r['genre']=='文言文' for r in READINGS)==472
    assert sum(r['genre']=='诗歌' for r in READINGS)==269
    for row in READINGS:
        key=bank.body_hash(row['body']);assert key not in hashes;hashes.add(key)
        assert row['author'] and len(row['body'].encode())<=60000
        assert '译文' not in row and '鉴赏' not in row and 'questions' not in row
        entry=catalog.get_entry(row['id'].replace('expanded:','extra-').replace(':','-'))
        assert entry['collection']=='训练材料' and entry['books']==[] and not entry['recommended']
        assert entry['available'] and entry['analysis_source']=='内置研读解析（规则辅助）'
    records=bank.seed_records();assert len(records)==1345
    assert len({r['id'] for r in records})==1345
    assert sum(len(r['questions']) for r in records)==270


def test_objective_answers_still_align_with_source_numbers_and_complete_choices():
    data=Path(__file__).parents[1]/'backend/data'
    source={str(r['index']):r for r in json.loads((data/'gaokao_modern_objective.json').read_text())['example']}
    assert len(MODERN)==28 and sum(len(r['questions']) for r in MODERN)==84
    ids=set();fingerprints=set()
    for material in MODERN:
        original=source[material['id'].rsplit(':',1)[1]]
        assert material['body'] in original['question']
        assert len(material['body'])>=180 and '署名待核对'!=material['title']
        for question in material['questions']:
            number=int(question['id'].rsplit(':',1)[1])
            assert question['reference']=='正确选项：'+original['answer'][number-1]+'。'
            assert question['analysis'] and question['level']=='未分层' and question['max_score']==original['score']==3
            assert all(re.search(c+r'[．.、]',question['prompt']) for c in 'ABCD')
            assert question['id'] not in ids;ids.add(question['id'])
            fingerprint=bank.body_hash(material['body'])+bank.normalized(question['prompt'])+question['reference']
            assert fingerprint not in fingerprints;fingerprints.add(fingerprint)
            assert set(question['tags'])<=set(bank.TAG_LABELS)
    manifest=json.loads((data/'expansion_manifest.json').read_text())
    assert all(x['accepted'] and x['source_answers']==x['parsed_questions']==3 for x in manifest['exam_audit'])
    assert manifest['external_only'] and '2023' in manifest['external_only'][0]['reason']


def test_added_public_reading_opens_with_grounded_rules_and_confirmation_stays_private(teacher_client):
    c=teacher_client
    row=next(r for r in READINGS if r['genre']=='文言文' and r['author']=='苏轼')
    entry_id=row['id'].replace('expanded:','extra-').replace(':','-')
    opened=c.post('/api/catalog/'+entry_id+'/open').json()
    result=c.post('/api/articles/'+str(opened['id'])+'/analyze',json={}).json()
    assert result['source']=='内置研读解析（规则辅助）'
    assert all(p['evidence'] in row['body'] for p in result['points'])
    for point in result['points']:analysis.AnalysisPoint(**point)
    response=c.post('/api/articles/'+str(opened['id'])+'/confirm-analysis',json={k:result[k] for k in ['source','article_digest','points']})
    assert response.json()['created']==len(result['points'])
    assert c.post('/api/register',json={'username':'expansion_b','password':'separate-password-9283'}).status_code==200
    assert c.get('/api/workspace').json()['points']==[]
    other=c.post('/api/catalog/'+entry_id+'/open').json()['id'];assert other!=opened['id']
    m=next(x for x in MODERN if x['title']=='金石书画漫谈')
    reading=c.get('/api/question-links/articles?q=金石书画漫谈').json()['items'][0]
    assert reading['author']=='启功'
    questions=c.get('/api/question-library',params={'article':reading['id'],'knowledge_id':'tag-information','q':'金石书画漫谈','limit':50}).json()
    assert any(q['article']['id']==reading['id'] for q in questions['items'])
    question=c.get('/api/question-links/questions/bank:'+m['questions'][0]['id']).json()
    assert question['article']['title']=='金石书画漫谈' and question['reference']=='正确选项：C。'


def test_reseeding_keeps_existing_managed_question_ids_and_teacher_data(teacher_client):
    import backend.main as m
    c=teacher_client
    article=c.post('/api/articles',json={'title':'已有私有材料','genre':'阅读','content':'私有原文'}).json()['id']
    before=c.get('/api/workspace').json()
    with m.DB() as db:
        m.seed_material_bank(db);db.commit();m.seed_material_bank(db);db.commit()
    assert c.get('/api/workspace').json()==before
    old=c.get('/api/bank/materials/curated:deng-gao').json()
    assert len(old['questions'])==9 and old['questions'][0]['id'].startswith('curated:deng-gao:')
    assert c.get('/api/catalog').json()['bank_materials']==1345
