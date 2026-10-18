"""Topic modules: one snake_case file per topic, each exporting ``TOPIC``.

Authoring pattern (fixed by ``python_language.py``, the exemplar):

- One module per topic here, named for the topic id (``python-language`` →
  ``python_language.py``), exporting exactly ``TOPIC: Topic``.
- Sections teach concept-first, in curriculum order; every section has at
  least 2 blocks including a text block; ids are kebab-case, unique.
- Code blocks in must-source languages quote REAL repo files verbatim
  (repo-root-relative ``source``) and pass the snippet ratchet — write the
  real implementation first, then quote it; only concepts with no real
  counterpart get a tested exhibit under ``guide/domain/teaching/``.
- The topic's live demo block sits INLINE in the section that teaches it,
  never queued at the page end; its id is ``<area>:<name>`` and its
  endpoint lives at ``routers/demo/<area>.py`` over a pure builder in
  ``guide/domain/demos/``.
- List blocks structure enumerable content only (block-selection standard):
  3–8 items of "Lead term — explanation.", ``ordered`` only when sequence
  matters, no nesting; connecting prose stays around them.
- The LAST section is always the terminal companion (curl tour, bash
  blocks — exempt from sourcing).

``registry.py`` imports every topic module and constructs the production
registry from them — validation runs at import, so broken content fails
the process at startup.
"""
