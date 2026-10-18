"""The db domain vocabulary: UUIDv7 ids, the audit pattern, introspection rows.

This package is the schema topic's domain half: pure, typed, free of any
driver import. ``ids`` mints UUIDv7s (a real, tested implementation —
Python 3.13's stdlib has no ``uuid7``), ``audit`` defines the audit-log
event and its values, and ``ports`` names the seams adapters implement
(schema introspection). Topic 17's SQL access and topic 18's ORM sessions
will grow their own ports here.
"""
