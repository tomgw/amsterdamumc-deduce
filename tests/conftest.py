import pytest

from deduce import Deduce


@pytest.fixture(scope="session")
def model():
    return Deduce(config="../base_config.json", build_lookup_structs=False)
