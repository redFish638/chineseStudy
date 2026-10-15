"""Read-only article / common-knowledge / question index over existing records."""
from . import bank, catalog, knowledge


def build(materials, saved_articles, points, teaching_questions, assignment_counts):
    articles, questions = {}, {}
    saved_ids = {}
    catalog_by_hash = {bank.body_hash(x['content']):x for x in catalog.CATALOG if x['available']}

    def reading(title, body, genre, author='', source=''):
        digest = bank.body_hash(body)
        key = 'reading-'+digest
        entry = catalog_by_hash.get(digest)
        article = articles.setdefault(key, dict(id=key,title=entry['title'] if entry else title,
            author=entry['author'] if entry else author,genre=entry['genre'] if entry else genre,
            source=source,body=body,catalog_id=entry['id'] if entry else None,
            bank_ids=[],saved_ids=[],aliases=[],categories={},notes=[],confirmed_points=[],question_ids=[]))
        if title not in article['aliases']: article['aliases'].append(title)
        return article

    def add_categories(article, categories):
        for category in categories: article['categories'][category['id']] = category

    def tag_categories(tags):
        return [dict(id='tag-'+tag,name=bank.TAG_LABELS[tag],tag=tag) for tag in bank.TAG_LABELS if tag in tags]

    def add_question(question, article, categories):
        if not categories: categories=[dict(id='unclassified',name='知识点待确认',tag='')]
        question.update(article=dict(id=article['id'],title=article['title']),knowledge=categories)
        questions[question['id']]=question
        article['question_ids'].append(question['id'])
        add_categories(article,categories)

    for material in materials:
        article=reading(material['title'],material['body'],material['genre'],material['author'],material['source_label'])
        article['bank_ids'].append(material['id'])
        valid_notes=[n for n in material['notes'] if knowledge.grounded_note(n,material['body'])]
        note_tags={tag for n in valid_notes for tag in n.get('tags',[])}
        add_categories(article,tag_categories(material['tags'] if not material.get('managed',True) else note_tags))
        seen={(n['name'],n.get('evidence','')) for n in article['notes']}
        for note in valid_notes:
            if (note['name'],note.get('evidence','')) not in seen:
                article['notes'].append(note);seen.add((note['name'],note.get('evidence','')))
        for question in material['questions']:
            tags=question['tags']
            if question['id'].startswith('gaokao:'):
                direct=set(bank.tags_in(question['prompt']))|note_tags
                tags=[tag for tag in tags if tag in direct]
            add_question(dict(id='bank:'+question['id'],original_id=question['id'],origin='bank',
                bank_material_id=material['id'],point_id=None,level=question['level'],prompt=question['prompt'],
                material=material['body'],reference=question['reference'],analysis=question['analysis'],rubric='',
                max_score=question['max_score'],source=question['source'],year=material['year'],region=material['region'],
                assignment_count=0,tag_basis='题目原有标签结合题干和解析依据归类，已排除泛用答题方法，待教师核对',article_basis='题库题目所属阅读材料',goal_article=None),
                article,tag_categories(tags))

    for row in saved_articles:
        article=reading(row['title'],row['content'],row['genre'],source='教师教学文章')
        article['saved_ids'].append(row['id']);saved_ids[row['id']]=article['id']
    point_map={p['id']:p for p in points}
    for point in points:
        article=articles[saved_ids[point['article_id']]]
        categories=knowledge.categories(point['name'],point['description'])
        add_categories(article,categories)
        article['confirmed_points'].append({**point,'categories':categories})

    # Resolve the actual reading material, which can differ from the article
    # whose learning goal is used to train the student. Never mislabel it.
    for question in teaching_questions:
        point=point_map[question['point_id']]
        owner=articles[saved_ids[point['article_id']]]
        key='reading-'+bank.body_hash(question['material'])
        article=articles.get(key)
        basis='正文匹配已收录文章'
        if article is None:
            text=bank.normalized(question['material'])
            matches=[a for a in articles.values() if len(text)>=35 and text in bank.normalized(a['body'])]
            if len(matches)==1: article=matches[0];basis='选段唯一匹配已收录文章，待教师核对'
        if article is None:
            article=reading('自定义训练材料 #'+str(question['id']),question['material'],owner['genre'],source='教师题目材料，篇名待核对')
            basis='未唯一匹配文章；保留题目实际材料，不推断所属篇名'
        add_question(dict(**{k:question[k] for k in ['level','prompt','material','reference','rubric','max_score','point_id']},
            id='teaching:'+str(question['id']),original_id=question['id'],origin='teaching',bank_material_id=None,
            analysis='',source='教师保存的分层训练题',year='',region='',assignment_count=assignment_counts.get(question['id'],0),
            tag_basis='按题目所属知识点归入通用知识点',article_basis=basis,
            goal_article=dict(id=owner['id'],title=owner['title'],saved_id=point['article_id'],point_name=point['name'])),
            article,knowledge.categories(point['name'],point['description']))

    for article in articles.values():
        article['knowledge_counts']={key:sum(any(c['id']==key for c in questions[qid]['knowledge']) for qid in article['question_ids']) for key in article['categories']}
    categories={}
    for article in articles.values():
        for key, category in article['categories'].items():
            node=categories.setdefault(key,dict(**category,article_ids=[],question_ids=[]))
            node['article_ids'].append(article['id'])
    for question in questions.values():
        for category in question['knowledge']: categories[category['id']]['question_ids'].append(question['id'])
    return dict(articles=articles,knowledge=categories,questions=questions,
        stats=dict(articles=len(articles),knowledge_points=len(categories),questions=len(questions),
                   bank_questions=sum(q['origin']=='bank' for q in questions.values()),
                   teaching_questions=sum(q['origin']=='teaching' for q in questions.values())))


def article_summary(article):
    return {**{k:article[k] for k in ['id','title','author','genre','source','bank_ids','saved_ids','aliases','catalog_id']},
            'knowledge':[{**c,'question_count':article['knowledge_counts'][c['id']]} for c in article['categories'].values()],'question_count':len(article['question_ids'])}


def knowledge_summary(category):
    return {**{k:category[k] for k in ['id','name','tag']},'article_count':len(category['article_ids']),
            'question_count':len(category['question_ids'])}


def question_summary(question):
    return {k:question[k] for k in ['id','original_id','origin','article','knowledge','level','prompt','max_score',
                                   'source','year','region','assignment_count','tag_basis','article_basis','goal_article']}
