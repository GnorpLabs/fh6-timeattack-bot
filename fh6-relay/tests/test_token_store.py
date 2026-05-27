import pytest
import token_store


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setattr(token_store, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(token_store, "CONFIG_DIR", tmp_path)


def test_load_config_returns_empty_dict_when_no_file():
    assert token_store.load_config() == {}


def test_is_setup_complete_false_when_no_file():
    assert token_store.is_setup_complete() is False


def test_save_setup_persists_all_fields():
    token_store.save_setup(
        api_url="https://bot.example.com",
        discord_id="123",
        discord_username="alice",
        token="abc123",
    )
    cfg = token_store.load_config()
    assert cfg["api_url"] == "https://bot.example.com"
    assert cfg["discord_id"] == "123"
    assert cfg["discord_username"] == "alice"
    assert cfg["token"] == "abc123"


def test_is_setup_complete_true_after_save():
    token_store.save_setup("https://x.com", "1", "alice", "tok")
    assert token_store.is_setup_complete() is True


def test_get_udp_port_defaults_to_20440():
    assert token_store.get_udp_port() == 20440


def test_get_udp_port_reads_from_config():
    token_store.save_setup("https://x.com", "1", "alice", "tok")
    cfg = token_store.load_config()
    cfg["udp_port"] = 9999
    token_store._save_raw(cfg)
    assert token_store.get_udp_port() == 9999


def test_update_token_replaces_only_token():
    token_store.save_setup("https://x.com", "1", "alice", "old")
    token_store.update_token("newtoken")
    cfg = token_store.load_config()
    assert cfg["token"] == "newtoken"
    assert cfg["discord_id"] == "1"


def test_load_config_returns_empty_dict_for_corrupt_json(tmp_path):
    token_store.CONFIG_FILE.write_text("{corrupt", encoding="utf-8")
    assert token_store.load_config() == {}
