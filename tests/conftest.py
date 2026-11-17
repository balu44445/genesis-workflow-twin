import json
from pathlib import Path

import pytest

from genesis.model import Snapshot

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def raw():
    return json.loads((ROOT / 'examples/vulnerable.json').read_text())


@pytest.fixture
def snapshot(raw):
    return Snapshot.model_validate(raw)
