"""Small curated starting library, not a complete textbook or licensed exam bank.
Ancient texts are public-domain originals; all teaching analysis is application-authored.
"""

def point(name, evidence, goal, explanation, foundation, consolidation, extension):
    return dict(name=name, evidence=evidence, learning_goal=goal, explanation=explanation,
                foundation=foundation, consolidation=consolidation, extension=extension)

CATALOG = [
    dict(id='deng-gao', title='登高', author='杜甫', genre='诗歌', collection='高中课文',
         content='风急天高猿啸哀，渚清沙白鸟飞回。\n无边落木萧萧下，不尽长江滚滚来。\n万里悲秋常作客，百年多病独登台。\n艰难苦恨繁霜鬓，潦倒新停浊酒杯。', points=[
             point('意象与悲秋意境', '风急天高猿啸哀，渚清沙白鸟飞回。', '能从景物、声音及修饰词概括悲凉意境。', '急风、哀猿与回飞之鸟共同构成凄清画面，不能只罗列意象而不分析其特点。', '找出首联的景物及声音。', '结合“急”“哀”分析意境。', '比较本诗与《沁园春·长沙》的秋景情感差异。'),
             point('时空对举与景物气势', '无边落木萧萧下，不尽长江滚滚来。', '能结合对举与叠词解释景物的空间感和动态感。', '“无边”“不尽”拓宽时空，“萧萧”“滚滚”强化动态；落木与长江也引出生命有限的感慨。', '解释“无边”“不尽”所写特点。', '从叠词与对偶分析颔联。', '论述宏阔之景与个人身世之悲的关系。'),
             point('关键词中的身世之悲', '万里悲秋常作客，百年多病独登台。', '能把羁旅、暮年、多病、孤独等信息与对应词语相联系。', '“万里”“常”“百年”“多病”“独”层层叠加，诗人之悲不只来自季节。', '圈出反映处境的关键词。', '用“词语—处境—情感”组织分析。', '联系尾联分析身世处境与时代艰难的交织，区分文本依据和背景推断。'),
         ]),
    dict(id='chi-bi-fu', title='赤壁赋（节选）', author='苏轼', genre='文言文', collection='高中课文',
         content='壬戌之秋，七月既望，苏子与客泛舟游于赤壁之下。清风徐来，水波不兴。举酒属客，诵明月之诗，歌窈窕之章。少焉，月出于东山之上，徘徊于斗牛之间。白露横江，水光接天。纵一苇之所如，凌万顷之茫然。浩浩乎如冯虚御风，而不知其所止；飘飘乎如遗世独立，羽化而登仙。', points=[
             point('文言实词与语境释义', '清风徐来，水波不兴。举酒属客', '能根据语境解释“徐”“兴”“属”，并落实到翻译。', '“徐”为缓缓，“兴”为起，“属”通“嘱”，这里指劝酒。解释需与泛舟饮酒的语境相合。', '解释“徐”“兴”“属”。', '翻译相关句子并说明语境依据。', '比较同一实词在不同篇目中的义项。'),
             point('状语后置与句式翻译', '月出于东山之上，徘徊于斗牛之间。', '能识别介词结构并在现代汉语中调整语序。', '“于东山之上”“于斗牛之间”交代处所，翻译时常调整到谓语前。斗牛指星宿。', '找出两个介词结构。', '完整翻译句子并还原语序。', '与“苏子与客泛舟游于赤壁之下”比较，概括该句式的翻译策略。'),
             point('写景层次与主观感受', '白露横江，水光接天。', '能从景物范围及人物感受分析写景与抒情的关系。', '清风水波写近景，江上白露与接天水光扩展视野；结尾由景物转向超然感受。本节选不能代表全篇情感变化。', '列出近景与远景。', '分析“横”“接”呈现的画面。', '联系“遗世独立”说明景物与人物精神状态的关系。'),
         ]),
    dict(id='quan-xue', title='劝学（节选）', author='荀子', genre='文言文', collection='高中课文',
         content='君子曰：学不可以已。\n青，取之于蓝，而青于蓝；冰，水为之，而寒于水。木直中绳，𫐓以为轮，其曲中规。虽有槁暴，不复挺者，𫐓使之然也。故木受绳则直，金就砺则利，君子博学而日参省乎己，则知明而行无过矣。\n吾尝终日而思矣，不如须臾之所学也；吾尝跂而望矣，不如登高之博见也。登高而招，臂非加长也，而见者远；顺风而呼，声非加疾也，而闻者彰。假舆马者，非利足也，而致千里；假舟楫者，非能水也，而绝江河。君子生非异也，善假于物也。', points=[
             point('中心论点与论证层次', '君子曰：学不可以已。', '能识别中心论点并梳理后文论证角度。', '开篇提出学习不可停止；节选分别从学习改变提升人和借助外物等角度论证，须区分论点与例证。', '找出中心论点。', '概括两个段落的论证角度。', '为“学不可以已”补充一个合乎逻辑的当代例证并说明其适用范围。'),
             point('比喻论证与类比推理', '青，取之于蓝，而青于蓝；冰，水为之，而寒于水。', '能解释喻体特点、观点及两者之间的逻辑联系。', '青与冰的变化说明经过学习可以提升自身。答题需要说明“为何能证明”，不能只写用了比喻。', '指出两个喻体。', '说明喻体与学习效果的对应关系。', '比较比喻论证和举例论证的论证方式。'),
             point('词类活用与重点实词', '假舟楫者，非能水也，而绝江河。', '能解释“假”“水”“绝”并准确翻译。', '“假”是借助，“水”在此作动词指游水，“绝”是横渡；不可照搬现代常用义。', '解释三个关键词。', '翻译全句并说明“水”的用法。', '与“非利足也”比较，分析不同活用对句意的影响。'),
         ]),
    dict(id='shi-shuo', title='师说（节选）', author='韩愈', genre='文言文', collection='高中课文',
         content='古之学者必有师。师者，所以传道受业解惑也。人非生而知之者，孰能无惑？惑而不从师，其为惑也，终不解矣。生乎吾前，其闻道也固先乎吾，吾从而师之；生乎吾后，其闻道也亦先乎吾，吾从而师之。吾师道也，夫庸知其年之先后生于吾乎？是故无贵无贱，无长无少，道之所存，师之所存也。', points=[
             point('古今异义与固定结构', '古之学者必有师。师者，所以传道受业解惑也。', '能解释“学者”“所以”并避免套用现代义。', '“学者”指求学的人；“所以”在此表示用来……的、……的凭借，不表示因果关系。', '解释“学者”“所以”。', '翻译“师者，所以传道受业解惑也”。', '比较“所以”在文言文中表凭借与表原因的不同语境。'),
             point('意动用法与翻译', '吾从而师之', '能识别“师”的意动用法并准确译出。', '“师之”是以之为师，“从而”应落实“跟从并且”的句意，不能当作现代连词。', '解释“师之”。', '完整翻译并说明词类活用。', '比较“吾师道也”与“吾从而师之”中“师”的用法。'),
             point('从师原则与论证主旨', '无贵无贱，无长无少，道之所存，师之所存也。', '能从限制条件和判断标准归纳从师原则。', '作者排除地位和年龄限制，把是否闻道作为择师的重要标准；分析须引用与原则对应的语句。', '找出不应限制从师的两类条件。', '用原文依据解释择师标准。', '联系现实讨论这一原则的意义，同时区分专业知识与其他评价标准。'),
         ]),
    dict(id='nian-nu-jiao', title='念奴娇·赤壁怀古', author='苏轼', genre='诗歌', collection='高中课文',
         content='大江东去，浪淘尽，千古风流人物。故垒西边，人道是，三国周郎赤壁。乱石穿空，惊涛拍岸，卷起千堆雪。江山如画，一时多少豪杰。\n遥想公瑾当年，小乔初嫁了，雄姿英发。羽扇纶巾，谈笑间，樯橹灰飞烟灭。故国神游，多情应笑我，早生华发。人生如梦，一尊还酹江月。', points=[
             point('炼字与壮阔意境', '乱石穿空，惊涛拍岸，卷起千堆雪。', '能结合动词与比喻分析画面的力量感。', '“穿”“拍”“卷”写出山势、水势和浪势，“雪”比喻浪花，共同表现雄奇壮阔的赤壁景象。', '找出三个动词。', '结合动词和比喻赏析画面。', '比较赤壁景象与周瑜形象在气势上的联系。'),
             point('人物塑造与对比', '谈笑间，樯橹灰飞烟灭。', '能分析人物细节及其与抒情主体的关系。', '从容的姿态与战果构成鲜明反差；周瑜功业与词人早生华发形成对照。', '概括周瑜的形象特点。', '说明“谈笑间”的表达效果。', '结合“早生华发”分析怀古与伤己的联系。'),
             point('怀古伤今与复杂情感', '人生如梦，一尊还酹江月。', '能结合全词分析感慨与自我排遣，避免单一化概括。', '结尾有对人生与功业的感慨，也有向江月酹酒的自我排遣；不宜仅凭“如梦”判为消极或旷达。', '解释“酹”的行为。', '联系上下文分析结尾情感。', '讨论豪放风格与复杂情绪如何同时存在。'),
         ]),
    dict(id='gui-yuan', title='归园田居（其一）', author='陶渊明', genre='诗歌', collection='高中课文',
         content='少无适俗韵，性本爱丘山。误落尘网中，一去三十年。羁鸟恋旧林，池鱼思故渊。开荒南野际，守拙归园田。\n方宅十余亩，草屋八九间。榆柳荫后檐，桃李罗堂前。暧暧远人村，依依墟里烟。狗吠深巷中，鸡鸣桑树颠。户庭无尘杂，虚室有余闲。久在樊笼里，复得返自然。', points=[
             point('比喻与情感寄托', '羁鸟恋旧林，池鱼思故渊。', '能解释喻体与抒情主体处境、愿望的对应关系。', '羁鸟、池鱼喻受束缚的自己；旧林、故渊寄托回归田园的愿望，需联系“尘网”“樊笼”理解。', '解释“羁鸟”“池鱼”。', '分析比喻中的情感。', '比较“尘网”与“自然”所代表的生活状态。'),
             point('白描与田园意境', '暧暧远人村，依依墟里烟。', '能从空间层次和描写方式分析田园画面。', '村落、炊烟等寻常景物以质朴语言呈现，远近相间，形成宁静安适的田园氛围。', '找出田园生活意象。', '结合白描分析意境。', '比较田园细节与前文抽象抒情的作用。'),
             point('以声衬静与主旨', '狗吠深巷中，鸡鸣桑树颠。', '能说明日常声响如何表现环境及人物心境。', '犬吠鸡鸣是田园生活的自然声息，衬出村居的宁静，并与返归自然后的自在相呼应。', '找出听觉描写。', '说明以声衬静的效果。', '联系末句分析外部环境与主体精神自由的关系。'),
         ]),
    dict(id='niao-ming-jian', title='鸟鸣涧', author='王维', genre='诗歌', collection='训练材料',
         content='人闲桂花落，夜静春山空。\n月出惊山鸟，时鸣春涧中。', points=[
             point('以动衬静', '月出惊山鸟，时鸣春涧中。', '能解释动态声响与环境幽静的关系。', '月升、鸟惊、间歇鸟鸣突出山中的寂静，不能把“有声音”直接判为热闹。', '指出动态与声音。', '分析以动衬静。', '与《归园田居》犬吠鸡鸣的写法比较。'),
             point('意象与闲适心境', '人闲桂花落，夜静春山空。', '能由细小景物与感受者状态分析心境。', '细微的花落与安静的山夜相联系，“人闲”提示主体的安宁闲适。', '列出意象。', '解释“闲”与景物感知的联系。', '论证外在寂静与内心宁静的关系。'),
         ]),
    dict(id='lun-yu-xue-si', title='《论语》学思二则', author='孔子弟子及再传弟子', genre='文言文', collection='训练材料',
         content='子曰：“学而不思则罔，思而不学则殆。”\n子曰：“温故而知新，可以为师矣。”', points=[
             point('文言虚词与语义关系', '学而不思则罔，思而不学则殆。', '能根据前后语义辨析“而”的作用。', '两处“而”均连接相反或相对的行为，表示转折；与“温故而知新”的承接关系不同。', '解释“而”。', '比较两则中“而”的用法。', '说明脱离语境机械对应虚词义项的局限。'),
             point('学习方法与对举论证', '学而不思则罔，思而不学则殆。', '能归纳学思结合的观点及对举的表达效果。', '从只学不思与只思不学两种偏差展开，强调学习与思考相互配合。', '解释“罔”“殆”。', '分析对举与主旨。', '联系《劝学》讨论思考与学习的关系。'),
         ]),
]

CATALOG.append(dict(id='he-tang-yue-se', title='荷塘月色（节选）', author='朱自清', genre='阅读', collection='高中课文',
    content='曲曲折折的荷塘上面，弥望的是田田的叶子。叶子出水很高，像亭亭的舞女的裙。层层的叶子中间，零星地点缀着些白花，有袅娜地开着的，有羞涩地打着朵儿的；正如一粒粒的明珠，又如碧天里的星星，又如刚出浴的美人。微风过处，送来缕缕清香，仿佛远处高楼上渺茫的歌声似的。', points=[
        point('比喻与景物特征', '叶子出水很高，像亭亭的舞女的裙。', '能解释比喻的本体、喻体及相似特点。', '以舞女的裙比喻荷叶，表现其舒展、轻盈的姿态；说明相似点比只写“生动形象”更具体。', '指出本体、喻体', '结合“亭亭”解释比喻表现的特点', '比较文中荷叶与荷花比喻的不同表达效果'),
        point('通感与多感官描写', '微风过处，送来缕缕清香，仿佛远处高楼上渺茫的歌声似的。', '能说明感官转换及其与景物特征的联系。', '由嗅觉的清香联想到听觉中远处渺茫的歌声，表现香气若有若无、轻柔缥缈的特点；通感也可借助比喻形式。', '指出句子涉及的两种感官', '说明感官转换的相似基础与作用', '另举一个通感例子并分析其成立的条件'),
        point('叠词与语言节奏', '曲曲折折的荷塘上面，弥望的是田田的叶子。', '能联系具体景物说明叠词的语义与节奏效果。', '“曲曲折折”写荷塘形态，“田田”写荷叶茂密；叠词既描绘景物特征，也形成舒缓的语音节奏。本节选不能单独证明全篇情感。', '找出叠词并解释其含义', '说明叠词对画面及节奏的作用', '比较将叠词改为普通词语后表达效果的变化'),
    ]))

for item in CATALOG:
    item['scope'] = '节选' if '节选' in item['title'] else '全文（所列作品或章句）'
    item['source'] = '公版作品原文（节选已标注）；解析为本应用编写，字句请与任教教材核对。非商业题库或高考真题。'
    for p in item['points']:
        assert p['evidence'] in item['content'], (item['id'], p['name'])


def get_entry(id):
    return next((x for x in CATALOG if x['id'] == id), None)


def match_entry(content, genre):
    return next((x for x in CATALOG if x['content'] == content and x['genre'] == genre), None)


def listing():
    return [{key: value for key, value in x.items() if key != 'points'} for x in CATALOG]

# Source links are reference portals, not claims that their full collections were imported.
RESOURCES = [
    {'name': '国家中小学智慧教育平台 · 教材入口', 'url': 'https://basic.smartedu.cn/',
     'note': '查找不同出版社、版本及册次；教材内容以平台及任教教材为准。', 'status': '官方入口；当前开发环境访问返回403，未完成在线核验'},
    {'name': 'GAOKAO-Bench · 2010—2022 高考题整理', 'url': 'https://github.com/OpenLMLab/GAOKAO-Bench',
     'note': '公开高考题研究数据，含语文题。项目README与Apache-2.0许可证已核验；不代表官方答案或所有年份。', 'status': '已联网核验并收录29组古诗阅读材料；年份卷别据原数据'},
    {'name': 'chinese-poetry · 古典文学公开数据', 'url': 'https://github.com/chinese-poetry/chinese-poetry',
     'note': '唐诗、宋词、论语等。已核验项目README及唐诗三百首中的《登高》，异体字与教材标点可能不同。', 'status': '已联网核验；不可当作完整教材目录'},
    {'name': '跨版本电子教材目录工具', 'url': 'https://github.com/maplexuci/pdf_book_download_from_zxxeducn',
     'note': '第三方目录工具，提供学段、学科、版本、册次维度；本应用未复制其教材文件，也不绕过平台访问限制。', 'status': '已联网核验项目说明；教材收录待逐项核对'},
]
for entry in CATALOG:
    entry['edition'] = '跨版本选篇（具体版本册次待核对）'
    entry['source_url'] = ''
    if entry['id'] == 'deng-gao':
        entry['source_url'] = 'https://github.com/chinese-poetry/chinese-poetry/blob/master/全唐诗/唐诗三百首.json'


def practice_candidates(name, genre):
    """Return authored, reviewable exercise drafts; never label them as internet exam questions."""
    def category(text):
        for words, key in [(['意动', '活用'], '活用'), (['意象', '意境', '写景', '白描'], '景物'),
                           (['衬静'], '动静'), (['实词', '古今'], '词义'), (['翻译', '句式'], '翻译'),
                           (['论点', '论证'], '论证'), (['情感', '身世', '主旨', '原则'], '主旨'),
                           (['炼字', '关键词'], '词语'), (['虚词'], '虚词'), (['比喻'], '比喻')]:
            if any(word in text for word in words): return key
        return None
    key = category(name)
    result = []
    for entry in CATALOG:
        if entry['genre'] != genre: continue
        for index, p in enumerate(entry['points']):
            if name != p['name'] and (not key or category(p['name']) != key): continue
            for level, direction in [('基础', 'foundation'), ('巩固', 'consolidation'), ('拓展', 'extension')]:
                result.append({'id': entry['id']+'-'+str(index)+'-'+level, 'title': entry['title'],
                    'level': level, 'material': entry['content'], 'prompt': p[direction]+'。请结合所给材料作答。',
                    'reference': '参考思路（教师需结合具体问题完善）：'+p['explanation'],
                    'rubric': '待教师完善分层采分点：准确理解关键语句（3分）；提供相应文本依据（3分）；围绕题目完成分析（4分）。',
                    'max_score': 10, 'source': '应用自编练习草稿，非高考真题；原文为公版作品',
                    'matched_point': p['name']})
    return result[:36]

# Public exam material. Original file retained unchanged alongside upstream license and attribution.
import json
import re
from pathlib import Path


def quoted_evidence(text, material):
    compact = ''.join(c for c in material if not c.isspace())
    positions = [i for i, c in enumerate(material) if not c.isspace()]
    for quote in re.findall(r'[“「]([^”」]{1,100})[”」]', text):
        needle = ''.join(quote.split())
        start = compact.find(needle)
        if needle and start >= 0:
            return material[positions[start]:positions[start+len(needle)-1]+1]
    lines = [line.strip() for line in material.splitlines() if len(line.strip()) > 8 and not line.strip().startswith('阅读')]
    return lines[0][:100] if lines else material[:100]


def extract_exam_points(record, material):
    published = record.get('analysis', '') or record.get('answer', '')
    candidates = [
        ('景物与意境', r'意象|意境|环境|景物|景色', '能从原文景物及修饰语概括环境特点，并说明其作用。'),
        ('思想情感', r'情感|感情|思乡|思念|心情|志向|情绪|感慨', '能以文本依据支撑情感判断，区分作者处境与读者推测。'),
        ('表现手法', r'衬|比喻|拟人|对比|虚实|动静|用典|烘托|通感|象征', '能识别具体表现手法，并解释它如何服务于内容与情感。'),
        ('词句赏析', r'炼字|词语|叠词|动词|关键词|含义', '能结合语境解释词句含义，并分析表达效果。'),
        ('结构与章法', r'结构|照应|承上|铺垫|线索|首尾', '能说明诗句之间的关系及其对表达的作用。'),
    ]
    result = []
    for name, pattern, goal in candidates:
        match = re.search(pattern, published)
        if not match: continue
        start = max(0, match.start()-80)
        excerpt = published[start:start+480].strip()
        evidence = quoted_evidence(excerpt+'\n'+published, material)
        result.append(point(name, evidence, goal, '据公开题目解析摘取（须复核）：'+excerpt,
            '结合引文解释与“'+name+'”有关的关键词句',
            '完成所附原题中与“'+name+'”有关的要求，写出依据与分析',
            '另选同类作品，比较“'+name+'”方面的异同并论证'))
    if not result:
        result.append(point('文本理解与题意', quoted_evidence(published, material), '能逐项回应原题要求并引用原文。',
            '据公开解析摘取（须复核）：'+published[:480], '解释题目关键词', '逐项回应原题并列出依据', '与另一篇材料比较阅读方法'))
    return result


EXAM_RECORDS = json.loads((Path(__file__).parent/'data/gaokao_poetry.json').read_text())['example']
EXAM_BY_ID = {}
for record in EXAM_RECORDS:
    question = record['question'].strip()
    parts = re.split(r'(?=（\s*1\s*）|\(\s*1\s*\))', question, maxsplit=1)
    material = parts[0].strip() if len(parts) == 2 else question
    exam_id = 'gaokao-poetry-'+str(record['index'])
    title = record['year']+'年'+record['category']+' · 古代诗歌阅读'
    entry = dict(id=exam_id, title=title, author='见材料署名', genre='诗歌', collection='公开真题材料',
        content=material, points=extract_exam_points(record, material), scope='试题所附材料',
        source='GAOKAO-Bench公开整理，年份与卷别据原数据；非官方校订版。',
        edition='高考题目（不按教材版本划分）',
        source_url='https://github.com/OpenLMLab/GAOKAO-Bench/blob/main/Data/Subjective_Questions/2010-2022_Chinese_Language_Ancient_Poetry_Reading.json',
        analysis_source='公开题目解析提取（非AI）')
    for p in entry['points']: assert p['evidence'] in material
    CATALOG.append(entry)
    EXAM_BY_ID[exam_id] = {'entry': entry, 'record': record, 'prompt': parts[1].strip() if len(parts) == 2 else question}

# Extend authored candidates with original published questions. Difficulty is a teacher-adjustable suggestion.
_authored_candidates = practice_candidates

def practice_candidates(name, genre):
    result = []
    if genre == '诗歌':
        for bundle in EXAM_BY_ID.values():
            entry, record = bundle['entry'], bundle['record']
            if not any(p['name'] in name or name in p['name'] for p in entry['points']): continue
            result.append({'id': entry['id']+'-original', 'title': entry['title'], 'level': '巩固',
                'material': entry['content'], 'prompt': bundle['prompt'],
                'reference': record['answer'], 'rubric': '参考原题满分与公开解析：'+record.get('analysis',''),
                'max_score': int(record['score']), 'matched_point': name,
                'source': 'GAOKAO-Bench公开题目整理；巩固层次为系统建议，非官方难度标定'})
    # Generated draft directions are only offered for the authored initial library.
    base_items = _authored_candidates(name, genre)
    base_items = [x for x in base_items if not x['id'].startswith('gaokao-')]
    return (result[:12]+base_items)[:36]

# Add factual directory entries and source-attributed public originals after legacy seeds.
from .curriculum import extend_catalog
extend_catalog(CATALOG)
