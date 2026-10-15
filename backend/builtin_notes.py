"""Packaged authored notes and transparent, text-grounded reading aids.

Rule aids identify observable language; they do not infer a poem's theme, a
speaker's biography, historical allusions, or definitive exam answers.
"""
import json
from pathlib import Path
import re

AUTHORED = json.loads((Path(__file__).parent/'data/authored_analysis.json').read_text())
RULE_SOURCE = '内置研读解析（规则辅助）'
AUTHORED_SOURCE = '内置篇目解析（待审校）'


def span(body, start, stop):
    """A contiguous sentence/clause, bounded for the analysis input contract."""
    left = max(0,start-100)
    boundaries=list(re.finditer(r'[。！？!?\n]',body[left:start]))
    if boundaries: left += boundaries[-1].end()
    right=min(len(body),stop+120)
    boundary=re.search(r'[。！？!?\n]',body[stop:right])
    if boundary:right=stop+boundary.end()
    value=body[left:right].strip()
    return value if len(value)<=300 else body[start:min(len(body),stop+120)].strip()


def point(name,evidence,explanation,foundation,consolidation,extension,tags):
    return dict(name=name,evidence=evidence,learning_goal='能引用原句辨析“'+name+'”，区分文本事实与需要论证的解释。',
                explanation=explanation,foundation=foundation,consolidation=consolidation,extension=extension,
                tags=tags,origin='rule')


def rule_notes(title,genre,body):
    """Bounded, deterministic aids with literal quotations; always marked for review."""
    if not body.strip():return []
    notes=[]
    def add(pattern,name,explain,base,consolidation,extension,tags):
        match=re.search(pattern,body)
        if match:
            quote=span(body,match.start(),match.end())
            token=match.group()
            notes.append(point(name,quote,'【规则辅助，待审校】原句出现“'+token+'”。'+explain,
                               base,consolidation,extension,tags))
    if genre=='诗歌':
        add(r'[愁悲恨哀怨憂忧悵怅喜樂乐歡欢泣淚泪]', '情感词与语气辨析',
            '这是可定位的情感语汇。须连同“不、莫、无”等否定、人物说话口吻及前后转折判断，不能据单个字断定全篇悲喜或作者身世。',
            '解释引句中情感词的含义，圈出与它相连的否定词或程度词。',
            '结合本句及相邻句，说明是谁的感受、是否有否定或转折，再概括局部情绪。',
            '找另一处同类情感词，比较相同词语在不同语气中的效果。',['emotion','wording'])
        add(r'明月|月光|月明|月色|月夜|夜月|月落|月出|落日|夕阳|夕陽|日光|[星雲云雨雪風风霜山水江河海花柳松竹鳥鸟雁猿]', '景物语汇与语境',
            '这类语汇为分析画面提供入口，但也可能用于比喻、典故或想象。应先辨清实景与非实景，联系修饰词、动作和人物处境再说明作用，不能把“月”直接等同于思乡。',
            '圈出引句中的景物语汇及相连的修饰词、动词。',
            '判断此处写的是可见景物、想象还是比喻；据原句说明画面特点与人物的联系。',
            '比较另一篇中相同景物的用法，论证它们为何可能表达不同情感。',['imagery'])
        add(r'[聞闻聽听鳴鸣啼嘯啸聲声喧響响]', '声音线索与感官描写',
            '句中有听觉或发声线索。分析时应交代声音来源、听者与声音特点；若要判断以声衬静，必须另找环境安静的证据，不能见声便认定衬静。',
            '辨认引句中听觉词的字面意思及其声音来源。',
            '结合相邻句说明声音如何进入画面；判断实听、想象或比拟，并列出依据。',
            '比较有声与无声描写的不同作用；只有证据充分时才使用以声衬静术语。',['wording'])
    elif genre=='文言文':
        add(r'曰|云：|云曰', '对话与叙述层次',
            '该处有引语标志。先核对说话者、听话者与引语范围，区分叙述者的说明和人物的主张；不能把人物说法直接当作作者结论。',
            '标出本句谁在说话、对谁说及直接引语的起止。',
            '结合前后人物反应，解释这句话在问答或事件推进中的作用。',
            '换用间接叙述改写本段，比较人物口吻和说服效果的变化。',['narration','information'])
        add(r'所以|是以|然则|然則|故|盖|蓋', '关联词与论说关系',
            '关联或推论语汇提示句间关系，但文言词可能多义。须先解释此处用法，再以相邻两句的内容验证是因果、说明还是其他关系，不可只凭字面套用现代义。',
            '联系前后句解释引句中的关联语汇。',
            '把前后句改写为现代汉语，说明二者关系，并核对是否存在省略信息。',
            '另选一处同词用例，比较词义或逻辑关系，说明不能机械套译的原因。',['translation','information'])
        add(r'之|其|以|而|于|於', '文言词义与指代核对',
            '虚实兼类词或多义词须在具体句子中确定用法。可依次检查是否指代人物事物、连接成分、引介对象或作实义动词；这里不自动判定单一义项。',
            '给引句补出必要主语，辨析所标词语是否有指代对象。',
            '比较两种可能译法，以句法位置及上下文排除不合适的一种。',
            '与另一篇相同词语比较，归纳同字不同义或同义不同句法的证据。',['classical-particle','translation'])
    else:
        add(r'因此|所以|因为|因為|然而|但是|不过|不過|由此|可见|可見', '句间逻辑与论证核对',
            '连接语提示句间推理或转折。应先区分这句话是作者判断、引述观点还是人物对白，再核对前文信息能否支持后文结论，不能仅凭连接词确认论证成立。',
            '划出关联词，分别概括其前后两句的意思。',
            '用自己的话复述句间关系，指出结论的依据和可能省略的条件。',
            '对比另一材料相似推理，检查前提改变后结论是否仍成立。',['information','argument'])
    if len(notes)<3:
        # Directly count sentence form; do not mechanically identify antithesis or a genre.
        units=[m for m in re.finditer(r'[^，。！？；、：\n]+[，。！？；、：]?',body)
               if len(re.sub(r'[^\w]','',m.group()))>=3 and len(m.group())<160]
        if units:
            a=units[0];b=units[1] if len(units)>1 else units[0]
            qa=a.group().strip();qb=b.group().strip()
            la=len(re.sub(r'[^\w]','',qa));lb=len(re.sub(r'[^\w]','',qb))
            quote=body[a.start():b.end()].strip()[:300]
            notes.append(point('语句长短与表达节奏',quote,
                f'【规则辅助，待审校】所列两个语段“{qa}”“{qb}”按可见文字计分别为{la}、{lb}字（不计标点）。'
                '可比较停顿、重复及语义关系；等长不自动等于对偶，句长也不能单独决定语气或文体。',
                '标注引句停顿，并检查字数统计是否包含题头或注释；先确定有效正文范围。',
                '朗读引句，联系词序、重复与语义说明节奏效果，指出需要人工确认的句法关系。',
                '改写为长短不同的句子，比较节奏变化，说明改写是否损失原意。',['wording']))
    if len(notes)<3:
        sentences=[m for m in re.finditer(r'[^。！？\n]+[。！？]?',body) if m.group().strip()]
        first=sentences[0] if sentences else re.search(r'\S+',body)
        last=sentences[-1] if sentences else first
        beginning=body[first.start():min(first.end(),first.start()+100)].strip()
        ending=body[max(last.start(),last.end()-100):last.end()].strip()
        notes.append(point('首尾内容与信息推进',beginning,
            '【规则辅助，待审校】当前材料起首可见“'+beginning+'”，末尾可见“'+ending+'”。'
            '先分别概括两处直接信息，再判断有无内容变化或联系；不能预设首尾照应、卒章显志。若材料为节选，只分析这个选段的边界。',
            '分别概括当前选段起首与末尾的信息，不补写未给出的情节。',
            '用原句说明首尾在人、事、景或观点上的变化；如无明确对应，也应如实说明。',
            '补读可靠全文后比较选段边界与全篇结构，说明原判断的适用范围。',['structure','information']))
    return notes[:4]
