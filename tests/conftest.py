import pytest

from elkscout.testkit import make_fixtures


@pytest.fixture(scope="session")
def fixture_manual_dir(tmp_path_factory):
    """A data/manual/-shaped directory with the procedural mountain AOI."""
    out = tmp_path_factory.mktemp("fixtures") / "manual"
    make_fixtures(out)
    return out
