import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

app = FastAPI()


@pytest.fixture(scope="module")
def test_app():
    client = TestClient(app)
    yield client  # this is where the testing happens
