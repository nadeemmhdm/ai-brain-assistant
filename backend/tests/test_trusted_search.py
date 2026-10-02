from app import trusted_search

def test_authoritative_domains_rank_above_general_web():
    assert trusted_search.authority_score("https://www.nist.gov/x", "A") > trusted_search.authority_score("https://example.com/x", "C")

def test_community_sources_are_not_authoritative():
    assert trusted_search.authority_score("https://reddit.com/r/test", "D") <= .20

def test_lexical_relevance_requires_query_terms():
    assert trusted_search.lexical_score("python ssl", "Python SSL documentation") > trusted_search.lexical_score("python ssl", "cooking recipe")
