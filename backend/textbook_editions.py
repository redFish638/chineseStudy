"""Edition-specific placement, independent of shared article bodies.

The unified edition uses the existing sourced curriculum directory. The legacy
Jiangsu list is a partial reference index, not a complete/current textbook claim.
"""
EDITIONS = [
    {'id': 'renjiao', 'name': '人教版（统编）', 'publisher': '人民教育出版社',
     'note': '据现有统编五册参考目录；跨印次差异请按任教教材核对。'},
    {'id': 'sujiao', 'name': '苏教版（旧课标参考）', 'publisher': '江苏教育出版社',
     'note': '仅收录部分旧课标必修篇目对应关系，并非完整目录；册次及选段请按任教教材核对。'},
]

# Reference placement for the legacy five-volume compulsory series. Exact
# excerpt boundaries and variant titles remain those of the selected article.
SUJIAO = {
    '必修一': ['劝学', '师说', '赤壁赋', '始得西山宴游记'],
    '必修二': ['六国论', '阿房宫赋'],
    '必修三': ['烛之武退秦师', '谏太宗十思疏', '廉颇蔺相如列传', '鸿门宴'],
    '必修四': ['季氏将伐颛臾', '寡人之于国也', '滕王阁序'],
    '必修五': ['陈情表', '项脊轩志', '报任安书', '逍遥游', '兰亭集序'],
}


def attach_editions(catalog):
    from .curriculum import title_key
    for entry in catalog:
        placements = []
        if entry['books']:
            placements.append({'id': 'renjiao', 'books': list(entry['books'])})
        key = title_key(entry['title'])
        books = [book for book, titles in SUJIAO.items()
                 if any(title_key(title) == key for title in titles)]
        if books:
            placements.append({'id': 'sujiao', 'books': books})
        entry['textbook_editions'] = placements
