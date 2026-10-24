"""The scaling domain area: topic 40's state-placement port.

The topic's subject is where state LIVES, and its one external dependency
is the smallest thing that can prove the lesson: a counter whose value
lives outside the process. ``ports.py`` defines the ``SharedCounterStore``
Protocol the redis adapter implements over the shared client — the same
optional-service discipline as every store in this repo. Everything else
the topic teaches is introspection of state this app already carries.
"""
