import merlin
import merlin.app
import merlin.core


def test_merlin_package_imports() -> None:
    assert merlin is not None
    assert merlin.core is not None
    assert merlin.app is not None
