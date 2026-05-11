"""Shared test fixtures for Pulse test suite."""

import pytest


@pytest.fixture
def siyuan_success_response() -> dict:
    """Mock response returned by SiYuan API on successful block creation."""
    return {
        "code": 0,
        "data": [{"doOperations": [{"id": "test-block-id-abc123"}]}],
    }