import pytest

from ayah_app import create_app
from ayah_app.data import QuranRepository


@pytest.fixture(scope="session")
def repository():
    return QuranRepository.load()


@pytest.fixture(scope="session")
def app(repository):
    return create_app(repository=repository, testing=True)


@pytest.fixture()
def client(app):
    return app.test_client()
