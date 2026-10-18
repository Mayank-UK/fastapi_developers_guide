"""Dependency providers: the seams handlers declare with ``Depends``.

``guide.core`` keeps providers that are app-wide infrastructure beside the
thing they provide (``get_config``, ``get_scenario_store``); this package is
for the rest — real dependencies that exist as themselves, starting with the
request-span instrument (``request_span.py``, the yield dependency the
dependency topic teaches and the dep demos run live) and the dependency
flavors the dep:matrix demo resolves (``demo_flavors.py``).
"""
