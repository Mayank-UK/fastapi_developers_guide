"""The webhooks domain area: HMAC signing and the retry policy.

Topic 14's real in-repo substrate. A webhook inverts every API this guide
built — the server CALLS the client — so the two facts a sender and a
receiver must share are both here: proof of WHO sent a delivery (the
HMAC signer/verifier pair over a shared secret) and WHAT happens when the
receiver cannot take it (the pure retry-policy engine: the schedule, the
attempt budget, and the dead-letter verdict when the budget is spent).

``domain/demos/webhook_simulator.py`` packages these over a simulated
delivery lifecycle; ``routers/demo/api.py`` exposes the simulator plus a
REAL receive endpoint that verifies with the verifier below.
"""
