from news_parser.ticker_match import TickerMatcher


def test_match_by_symbol():
    matcher = TickerMatcher([
        {"id": 1, "ticker": "GAZP", "names": ["Газпром"]},
    ])
    matches = matcher.match("Газпром (GAZP) объявил о выплате дивидендов")
    assert len(matches) == 1
    assert matches[0].ticker_id == 1


def test_match_by_name():
    matcher = TickerMatcher([
        {"id": 2, "ticker": "SBER", "names": ["Сбербанк"]},
    ])
    matches = matcher.match("Сбербанк представил отчетность")
    assert len(matches) == 1
    assert matches[0].mention_type == "name"
