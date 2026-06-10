from unittest.mock import MagicMock
from c4000_lib.features.config import ConfigFeature
from c4000_lib.core import ModemError

class FakeResp:
    headers = {}
    def iter_content(self, chunk_size=8192):
        yield b"data"

def test_backup_returns_path_on_success(tmp_path, monkeypatch):
    import c4000_lib.features.config as cfg
    monkeypatch.setattr(cfg, "BACKUP_DIR", str(tmp_path))
    control = MagicMock()
    control.send_download.return_value = FakeResp()
    feature = ConfigFeature(control)
    feature._get_modem_identity = MagicMock(return_value=("C4000", "SN1"))
    result = feature.backup()
    assert result is not None and str(tmp_path) in result

def test_backup_returns_none_on_failure(tmp_path, monkeypatch):
    import c4000_lib.features.config as cfg
    monkeypatch.setattr(cfg, "BACKUP_DIR", str(tmp_path))
    control = MagicMock()
    control.send_download.side_effect = ModemError("boom")
    feature = ConfigFeature(control)
    assert feature.backup() is None
