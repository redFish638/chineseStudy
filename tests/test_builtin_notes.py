from types import SimpleNamespace

from backend import analysis, bank, catalog
from backend.builtin_notes import AUTHORED, RULE_SOURCE, rule_notes
from test_catalog import teacher_client


def test_every_readable_catalog_entry_has_article_specific_validated_notes():
    assert len(AUTHORED)==98
    assert sum(len(x) for x in AUTHORED.values())==232
    for entry in catalog.CATALOG:
        if not entry['available']:
            assert not entry['points'] and not entry['has_analysis']
            continue
        result=analysis.analyze(SimpleNamespace(**{k:entry[k] for k in ['title','genre','content']}))
        assert result['points']
        for point in result['points']:
            analysis.AnalysisPoint(**point)
            assert point['evidence'] in entry['content']
            assert all(point[k] for k in ['foundation','consolidation','extension'])
    # Specific interpretations, not interchangeable generic topic lists.
    short=AUTHORED['短歌行'];li=AUTHORED['李凭箜篌引']
    assert any('周公' in p['explanation'] and '求贤' in p['name']+p['explanation'] for p in short)
    assert any('玉碎' in p['explanation'] for p in li)
    assert not set(p['explanation'] for p in short)&set(p['explanation'] for p in li)


def test_every_packaged_bank_material_has_grounded_notes_and_no_new_fabricated_questions():
    records=bank.seed_records()
    assert len(records)==1345
    assert sum(len(x['questions']) for x in records)==270
    assert len({x['revision'] for x in records})==1345
    for row in records:
        assert row['notes']
        for note in row['notes']:
            assert note['evidence'] in row['body']
            assert set(note['tags'])<=set(bank.TAG_LABELS)
            if note['origin'] in {'rule','authored'}:
                analysis.AnalysisPoint(**{k:note[k] for k in analysis.AnalysisPoint.model_fields})
            if note['origin']=='rule':assert '规则辅助' in note['explanation']
    assert bank.point_tags('用典与求贤主旨')==['allusion']


def test_rules_do_not_turn_keywords_into_definitive_theme_or_figure():
    for genre,body in [('诗歌','莫愁前路无知己，天下谁人不识君。'),('诗歌','床前明月光，疑是地上霜。'),('文言文','子曰：“学而时习之，不亦说乎？”')]:
        notes=rule_notes('测试材料',genre,body)
        assert len(notes)>=2
        assert all(n['evidence'] in body and n['origin']=='rule' for n in notes)
    emotion=rule_notes('别董大','诗歌','莫愁前路无知己，天下谁人不识君。')[0]
    assert '否定' in emotion['explanation']
    assert '悲伤' not in emotion['explanation']
    moon=next(n for n in rule_notes('静夜思','诗歌','床前明月光，疑是地上霜。') if n['name']=='景物语汇与语境')
    assert '不能把“月”直接等同于思乡' in moon['explanation']
    assert rule_notes('空目录','诗歌','')==[]


def test_rule_bank_material_can_be_previewed_confirmed_and_recommended_with_honest_provenance(teacher_client):
    c=teacher_client
    records=bank.seed_records()
    row=next(x for x in records if all(n['origin']=='rule' for n in x['notes']) and x['genre']=='诗歌')
    detail=c.get('/api/bank/materials/'+row['id']).json()
    assert detail['notes'] and '规则辅助' in detail['review']
    result=c.post('/api/bank/materials/'+row['id']+'/open').json()
    assert result['has_analysis']
    response=c.post(f"/api/articles/{result['id']}/analyze",json={})
    assert response.status_code==200,response.text
    output=response.json()
    assert output['source']==RULE_SOURCE
    assert all(p['evidence'] in row['body'] for p in output['points'])
    saved=c.post(f"/api/articles/{result['id']}/confirm-analysis",json={k:output[k] for k in ['article_digest','source','points']})
    assert saved.status_code==200 and saved.json()['created']==len(output['points'])
    point=c.get('/api/workspace').json()['points'][0]
    assert RULE_SOURCE in point['description']
    _,ranked=bank.recommend(records,'景物语汇与语境','意象与意境','其他作品正文','其他作品','诗歌')
    rules=[x for x in ranked if all(n['origin']=='rule' for n in x['notes'])]
    assert rules
    for item in rules:
        if item['match_evidence']: assert '规则辅助' in item['match_basis']
        else: assert '关联较弱' in item['match_basis']
    stats=c.get('/api/bank').json()['stats']
    assert stats['analyzed']==1345 and 0<stats['rule_analyzed']<1345


def test_existing_unmanaged_import_without_notes_gets_read_only_aids_without_overwrite(teacher_client):
    from backend.main import DB,BankMaterial,adopt_legacy_records
    c=teacher_client
    with DB() as db:
        record=bank.material_record('old-import','校本旧导入','教师','诗歌','bank','月照山间水，风鸣竹里窗。','','教师提供',[],[])
        row=BankMaterial(id=record['id'],managed=False)
        from backend.main import assign_bank_material
        assign_bank_material(row,record)
        row.notes_json='[]';row.tags_json='[]';row.review='原有审核说明';db.add(row);db.flush();adopt_legacy_records(db);db.commit()
    detail=c.get('/api/bank/materials/old-import').json()
    assert detail['notes'] and all(n['origin']=='rule' for n in detail['notes'])
    opened=c.post('/api/bank/materials/old-import/open').json()
    assert opened['has_analysis']
    output=c.post(f"/api/articles/{opened['id']}/analyze",json={}).json()
    assert output['source']==RULE_SOURCE
    with DB() as db:
        row=db.get(BankMaterial,'old-import')
        assert row.notes_json=='[]' and row.tags_json=='[]' and row.review=='原有审核说明'
