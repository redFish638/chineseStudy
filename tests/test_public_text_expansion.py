import json
from pathlib import Path
from urllib.parse import urlsplit

from backend import catalog
from test_catalog import teacher_client


def test_new_public_texts_have_whole_boundaries_and_exclude_neighbor_and_publisher_notes():
    records=json.loads((Path(__file__).parents[1]/'backend/data/curriculum.json').read_text())
    by={x['title']:x for x in records}
    assert by['祝福']['content'].startswith('旧历的年底')
    assert by['祝福']['content'].endswith('无限的幸福。')
    assert by['林教头风雪山神庙']['content'].endswith('便出庙门投东去。')
    assert '别里科夫' not in by['林教头风雪山神庙']['content']
    assert '郭沫若' not in by['红烛']['content'] and '昌耀' not in by['红烛']['content']
    assert '我小心地探出前额' not in by['红烛']['content']
    assert '王愿坚' not in by['小二黑结婚（节选）']['content']
    assert by['苏武传']['content'].endswith('须发尽白。')
    assert by['孔雀东南飞并序']['content'].endswith('戒之慎勿忘！')
    for x in records:
        if x.get('source_checked'):
            assert not any(s in x['content'] for s in ['学习本课','学习本文','本单元','课外搜集'])
            assert x.get('rights')
            assert urlsplit(x['text_source_url']).scheme=='https'
    assert '北冥' not in by['逍遥游']['content']
    assert '惠子谓庄子' in by['逍遥游']['content']
    assert '博學之' in by['中庸（节选）']['content']
    laozi=by['《老子》八章']
    assert sum(line.startswith('第') and line.endswith('章') for line in laozi['content'].splitlines())==8
    assert '译文' not in laozi['content'] and '①' not in laozi['content']
    assert '善为道' in laozi['source_checked'] and '善为士' in laozi['source_checked']


def test_every_remaining_directory_has_original_guide_and_official_reading_entry(teacher_client):
    c=teacher_client;data=c.get('/api/catalog').json()
    assert data['readable']==data['analyzable']==131
    assert data['guided_directories']==61
    missing=[x for x in data['items'] if not x['available']]
    assert len(missing)==61
    for row in missing:
        assert row['has_guide'] and row['guide']['topics'] and not row['has_analysis']
        assert row['content']==''
        assert '不是' in row['guide']['notice']
        parsed=urlsplit(row['reading_url'])
        assert parsed.scheme=='https'
        assert parsed.hostname in {'basic.smartedu.cn','r1-ndr.ykt.cbern.com.cn'}
        assert c.post('/api/catalog/'+row['id']+'/open').status_code==409
    assert c.get('/api/workspace').json()['articles']==[]


def test_new_originals_open_analyze_and_confirm_without_ai(teacher_client):
    c=teacher_client
    items=c.get('/api/catalog').json()['items']
    for title in ['拿来主义','祝福','芣苢','大学之道','小二黑结婚（节选）','《孟子》一则']:
        row=next(x for x in items if x['title']==title)
        opened=c.post('/api/catalog/'+row['id']+'/open').json()
        result=c.post(f"/api/articles/{opened['id']}/analyze",json={})
        assert result.status_code==200,result.text
        result=result.json()
        assert result['source']=='内置篇目解析（待审校）'
        assert len(result['points'])==3
        assert all(p['evidence'] in row['content'] for p in result['points'])
        assert c.post(f"/api/articles/{opened['id']}/confirm-analysis",json={k:result[k] for k in ['source','article_digest','points']}).json()['created']==3
    assert c.get('/api/knowledge-library').json()['stats']['confirmed_records']==18
