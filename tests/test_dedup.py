def test_dedup_primeira_vez_nao_e_duplicado():
    from dedup import DedupCache
    cache = DedupCache(ttl_seconds=600)
    assert cache.is_duplicate("MSG1", now=1000.0) is False


def test_dedup_segunda_vez_e_duplicado():
    from dedup import DedupCache
    cache = DedupCache(ttl_seconds=600)
    cache.is_duplicate("MSG1", now=1000.0)
    assert cache.is_duplicate("MSG1", now=1001.0) is True


def test_dedup_expira_apos_ttl():
    from dedup import DedupCache
    cache = DedupCache(ttl_seconds=600)
    cache.is_duplicate("MSG1", now=1000.0)
    assert cache.is_duplicate("MSG1", now=1700.0) is False


def test_dedup_id_vazio_nunca_e_duplicado():
    from dedup import DedupCache
    cache = DedupCache(ttl_seconds=600)
    assert cache.is_duplicate("", now=1000.0) is False
    assert cache.is_duplicate("", now=1001.0) is False


def test_dedup_limpeza_lazy_remove_expirados():
    from dedup import DedupCache
    cache = DedupCache(ttl_seconds=600)
    cache.is_duplicate("A", now=1000.0)
    cache.is_duplicate("B", now=1001.0)
    cache.is_duplicate("C", now=2000.0)
    assert len(cache._seen) == 1  # só "C" sobrou
