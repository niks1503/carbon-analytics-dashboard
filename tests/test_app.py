"""Integration tests for Streamlit app.py using Streamlit AppTest."""

from streamlit.testing.v1 import AppTest


def test_app_renders_without_exceptions():
    """Verify that app.py initializes and runs from top to bottom without exceptions."""
    at = AppTest.from_file("../app.py", default_timeout=30)
    at.run()
    assert not at.exception, f"app.py raised unhandled exception: {at.exception}"
    assert len(at.tabs) >= 5
    # Verify metrics grid rendered
    assert len(at.metric) >= 4


def test_app_scope_toggles():
    """Verify that toggling off a scope recalculates metrics without exceptions."""
    at = AppTest.from_file("../app.py", default_timeout=30)
    at.run()
    assert not at.exception

    # Toggle off Scope 1
    scope1_cb = at.checkbox(key="filter_scope1")
    scope1_cb.uncheck().run()
    assert not at.exception
    assert len(at.metric) >= 4


def test_app_all_scopes_disabled_gracefully_stops():
    """Verify that unchecking all scopes triggers informative banner without unhandled exception."""
    at = AppTest.from_file("../app.py", default_timeout=30)
    at.run()
    assert not at.exception

    at.checkbox(key="filter_scope1").uncheck()
    at.checkbox(key="filter_scope2").uncheck()
    at.checkbox(key="filter_scope3").uncheck()
    at.run()

    assert not at.exception
    assert len(at.info) > 0


def test_app_single_region_selection():
    """Verify that filtering down to a single region renders without error."""
    at = AppTest.from_file("../app.py", default_timeout=30)
    at.run()
    assert not at.exception

    at.checkbox(key="filter_all_regions").uncheck().run()
    assert not at.exception
    assert len(at.metric) >= 4
