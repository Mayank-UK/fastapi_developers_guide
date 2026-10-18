"""Inbound HTTP layer: routers, middleware, and dependencies.

Routers stay thin (parse -> delegate -> map Result to a response);
presentation may import core and domain, never the data layer."""
