import uuid
import pytest
from fastapi import HTTPException
from app.database.db import init_db
from app.services.request_budget import _consume


def test_weighted_allowance_stops_before_another_provider_call_and_resets_next_month():
    init_db()
    key='vision-test:'+uuid.uuid4().hex
    _consume(key,5,2026*12+10,5,86400)
    with pytest.raises(HTTPException) as failure:
        _consume(key,5,2026*12+10,1,86400)
    assert failure.value.status_code==429
    _consume(key,5,2026*12+11,5,86400)
