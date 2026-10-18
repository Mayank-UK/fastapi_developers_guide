"""Demo API routers, one module per demo area: ``routers/demo/<area>.py``.

Each topic's live demos get an area module here (``py.py`` for the
python-language topic, later ``runtime.py``, ``fastapi.py``, …) exposing
one thin ``router`` with prefix ``/api/demo/<area>``. The shared
scenario-toggle endpoint lives in ``scenario.py``. Routers stay thin:
parse/validate input → call a pure builder or store → return a typed
response model; demo payload logic lives in ``guide/domain/demos/``.
"""
