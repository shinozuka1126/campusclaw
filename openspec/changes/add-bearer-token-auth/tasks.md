## 1. Token login

- [x] 1.1 Add `POST /api/auth/login` for JSON or form credentials.
- [x] 1.2 Issue a short-lived signed bearer token only for valid credentials; reject invalid credentials without exposing password or token.
- [x] 1.3 Preserve the existing signed-cookie session for HTML navigation.

## 2. Bearer validation and authorization

- [x] 2.1 Parse and validate `Authorization: Bearer <token>` before protected requests.
- [x] 2.2 Reload the user from the database by token subject and enforce existing role and class checks.
- [x] 2.3 Reject missing, malformed, tampered, or expired tokens with 401 for API requests.

## 3. Browser demonstration

- [x] 3.1 Update the login page to obtain and store the token.
- [x] 3.2 Update the materials page to fetch `/api/materials` with the bearer header.
- [x] 3.3 Add tests for token issuance, cookie-free bearer access, invalid tokens, expiry, and class isolation.

## 4. Evidence

- [x] 4.1 Update README with token usage and Network-panel evidence instructions.
- [x] 4.2 Run the full test suite and strict OpenSpec validation.
