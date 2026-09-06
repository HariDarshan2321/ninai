-- Successful browser login counters start at rollout; do not infer historical logins
-- from oauth_identities.last_seen_at, which updates on API token validation too.
ALTER TABLE users ADD COLUMN last_login_at timestamptz;
ALTER TABLE users ADD COLUMN login_count bigint NOT NULL DEFAULT 0 CHECK (login_count >= 0);
-- Display-only OIDC profile fields. Identity and admin grants still use UUIDs.
-- Keep these separate from the legacy UNIQUE email: never merge by email.
ALTER TABLE users ADD COLUMN profile_email text;
ALTER TABLE users ADD COLUMN profile_name text;
CREATE INDEX users_last_login_idx ON users(last_login_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX users_signup_idx ON users(created_at DESC,id);
