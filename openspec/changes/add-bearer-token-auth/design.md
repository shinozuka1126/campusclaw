# Design

## Token format

Use a three-part base64url token (`header.payload.signature`) signed with HMAC-SHA256 using the configured `SECRET_KEY`. Claims include `sub`, `username`, `role`, `class_id`, `iat`, and `exp`. The server validates the signature and expiration, then reloads the user from SQLite by `sub`; role and class filters come from the database row.

## Request flow

`POST /api/auth/login` accepts JSON credentials and returns `access_token`, `token_type`, and `expires_in`; it also establishes the existing HTML session so a browser can navigate to `/materials`. The materials page reads the token from browser storage and fetches `/api/materials` with `Authorization: Bearer <token>`, producing a visible Network request for the course demonstration.

## Compatibility

The existing form `POST /login`, signed-cookie session, HTML redirects, and all existing class/role authorization rules remain unchanged. Invalid bearer credentials never silently fall back to a valid cookie when an Authorization header is supplied.
