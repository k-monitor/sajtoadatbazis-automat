from itertools import product

news = ['444', '444.hu', '24.hu', 'index', 'telex', 'origo', 'magyarnemzet', 'g7', 'népszava', 'bank360', 'hvg', 'hvg.hu', 'bbc', 'atv', 'átlátszó', 'atlatszo.hu', 'válasz online', 'valaszonline.hu', 'szabad európa', 'media1', 'rtl', 'mfor', 'mfor.hu']
news_names = ['444', '444.hu', '24.hu', 'index', 'telex', 'origo', 'magyarnemzet', 'g7', 'népszava', 'bank360', 'hvg', 'hvg.hu', 'bbc', 'atv', 'átlátszó', 'atlatszo.hu', 'válasz online', 'valaszonline.hu', 'szabad európa', 'media1', 'rtl', 'lap', 'portál', 'újság', 'hírportál', 'mfor', 'mfor.hu', 'pénzcentrum']

def same_news(article):
    if ':' in article.title and article.title.split(':')[0].lower() in news_names:
        return True
    for sent in product(['írja', 'írta', 'írta meg', 'tudta meg', 'számolt be', 'számolt be az esetről', 'mondta', 'számolt be', 'szúrta ki'], ['a', 'az'], news_names):
        if ' '.join(sent) in article.description.lower() or ' '.join(sent) in article.text.lower():
            return True
    for sent in product(news_names, ['-nak', 'nak', '-nek', 'nek'], [' adott'], [' interjú']):
        if ' '.join(sent) in article.description.lower() or ''.join(sent) in article.text.lower():
            return True
    for sent in product(['elismerte '], ['a ', 'az '], news_names, ['-nak', 'nak', '-nek', 'nek']):
        if ' '.join(sent) in article.description.lower() or ''.join(sent) in article.text.lower():
            return True
    for sent in product(news_names, ['vette észre', 'azt írja', 'bukkant rá', 'kiderítette']):
        if ' '.join(sent) in article.description.lower() or ' '.join(sent) in article.text.lower():
            return True
    for sent in product(['derül ki a'], news_names, ['riportjából']):
        if ' '.join(sent) in article.description.lower() or ' '.join(sent) in article.text.lower():
            return True
    for sent in product(news_names, ['riportjából kiderül', 'riportja szerint']):
        if ' '.join(sent) in article.description.lower() or ' '.join(sent) in article.text.lower():
            return True
    if article.text.strip().endswith(')'):
        for news_name in news_names:
            if article.text[article.text.rfind('('):].lower():
                return True

    return False

