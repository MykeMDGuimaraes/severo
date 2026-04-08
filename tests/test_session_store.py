import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_supabase(monkeypatch):
    """Substitui o cliente Supabase real por um mock."""
    mock_client = MagicMock()
    monkeypatch.setattr("session_store._client", mock_client)
    return mock_client


def _make_chain(mock_client, data=None):
    """Helper: configura a cadeia de chamadas .table().select()... .execute()"""
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=data or [])
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value = chain
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    mock_client.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_client.table.return_value.delete.return_value.lt.return_value.execute.return_value = MagicMock(data=[{"numero": "1"}, {"numero": "2"}])
    return chain


def test_get_retorna_none_quando_nao_existe(mock_supabase):
    _make_chain(mock_supabase, data=[])
    import session_store
    result = session_store.get("5511999", "whatsapp")
    assert result is None


def test_get_retorna_estado_quando_existe(mock_supabase):
    estado_salvo = {"fase": "qualificacao_lead", "messages": []}
    _make_chain(mock_supabase, data=[{"state": estado_salvo}])
    import session_store
    result = session_store.get("5511999", "whatsapp")
    assert result == estado_salvo


def test_set_chama_upsert(mock_supabase):
    _make_chain(mock_supabase)
    import session_store
    estado = {"fase": "qualificacao_lead", "messages": []}
    session_store.set("5511999", estado, "whatsapp")
    mock_supabase.table.assert_called_with("argos_sessions")
    mock_supabase.table.return_value.upsert.assert_called_once()


def test_delete_chama_delete(mock_supabase):
    _make_chain(mock_supabase)
    import session_store
    session_store.delete("5511999", "whatsapp")
    mock_supabase.table.assert_called_with("argos_sessions")


def test_cleanup_old_retorna_count(mock_supabase):
    _make_chain(mock_supabase)
    import session_store
    count = session_store.cleanup_old(days=30)
    assert count == 2
