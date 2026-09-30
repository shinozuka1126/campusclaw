# Bearer token authentication

## ADDED Requirements

### Requirement: Issue a bearer token
The system SHALL expose `POST /api/auth/login` accepting a username and password and SHALL return a short-lived `access_token` and `token_type` equal to `Bearer` for valid credentials. Invalid credentials MUST return 401 without an access token.

#### Scenario: Valid token login
- **WHEN** a client posts valid credentials
- **THEN** the response is 200 JSON with a three-part signed token and an expiration interval
- **AND** the existing browser session is established for HTML navigation

#### Scenario: Invalid token login
- **WHEN** a client posts an unknown username or incorrect password
- **THEN** the response is 401 and contains no access token

### Requirement: Authenticate bearer requests
Protected API routes SHALL accept `Authorization: Bearer <token>`; requests without a valid cookie session or bearer token SHALL receive 401. Malformed, tampered, or expired bearer tokens SHALL receive 401. When an Authorization header is present, an invalid token MUST NOT silently fall back to a cookie session.

#### Scenario: Bearer access to materials
- **WHEN** a client sends a valid bearer token to `/api/materials`
- **THEN** the request succeeds without a cookie
- **AND** the response contains only materials for the token subject's class

#### Scenario: Invalid bearer token
- **WHEN** a client sends an invalid or expired bearer token
- **THEN** the response is 401 and does not reveal material data

### Requirement: Preserve server-side authorization
The server SHALL reload the user by the token subject and SHALL derive role and class from the database. Client-supplied `class_id` claims or query parameters MUST NOT expand access.

#### Scenario: Cross-class isolation
- **WHEN** an A-class token requests B-class material or searches with a B-class parameter
- **THEN** the response does not contain B-class content

### Requirement: Browser sends Authorization
The materials page SHALL fetch `/api/materials` with an `Authorization: Bearer <token>` header when a token is stored after token login.

#### Scenario: Network evidence
- **WHEN** a user logs in through the browser and opens the materials page
- **THEN** the Network panel contains a materials request whose request headers include `Authorization: Bearer <token>`
