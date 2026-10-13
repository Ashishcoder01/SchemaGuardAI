
from unittest.mock import MagicMock

import pytest

from app.database import get_db


def test_get_db_rolls_back_and_closes_on_exception(monkeypatch):
    fake_session = MagicMock()

    monkeypatch.setattr(
        "app.database.SessionLocal",
        lambda: fake_session,
    )

    generator = get_db()

    assert next(generator) is fake_session

    with pytest.raises(RuntimeError, match="database failure"):
        generator.throw(RuntimeError("database failure"))

    fake_session.rollback.assert_called_once()
    fake_session.close.assert_called_once()
