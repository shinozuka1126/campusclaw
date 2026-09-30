# Bearer token authentication

## Why

The browser demonstration must show an `Authorization: Bearer <token>` header when requesting class materials. Keep the existing signed-cookie flow for HTML compatibility while adding a token flow for API clients and browser fetches.

## Scope

This change adds a JSON login endpoint, signed short-lived HS256-style bearer tokens, server-side user lookup, and browser fetches that send the token when loading materials. Existing cookie login, class isolation, and role checks remain supported.
