from news_parser.dedup import article_hash


def test_article_hash_stable():
    h1 = article_hash("Title", "https://example.com")
    h2 = article_hash("Title", "https://example.com")
    assert h1 == h2


def test_article_hash_changes():
    h1 = article_hash("Title", "https://example.com/a")
    h2 = article_hash("Title", "https://example.com/b")
    assert h1 != h2
