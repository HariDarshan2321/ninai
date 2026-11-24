-- Team opt-in, membership, and grants are independent of the legacy vault.
CREATE TABLE team_workspaces (
    workspace_id uuid PRIMARY KEY REFERENCES workspaces(id),
    enabled_at timestamptz NOT NULL DEFAULT now(),
    quarantined_at timestamptz,
    authorization_epoch bigint NOT NULL DEFAULT 0 CHECK (authorization_epoch >= 0)
);

CREATE TABLE team_members (
    workspace_id uuid NOT NULL REFERENCES team_workspaces(workspace_id),
    user_id uuid NOT NULL REFERENCES users(id),
    role text NOT NULL CHECK (role IN ('owner', 'admin', 'member')),
    created_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE team_projects (
    workspace_id uuid NOT NULL REFERENCES team_workspaces(workspace_id),
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 120),
    slug text NOT NULL CHECK (length(btrim(slug)) BETWEEN 1 AND 120),
    created_at timestamptz NOT NULL DEFAULT now(),
    archived_at timestamptz,
    PRIMARY KEY (workspace_id, id),
    UNIQUE (workspace_id, slug)
);

CREATE TABLE team_project_members (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role text NOT NULL CHECK (role IN ('member', 'maintainer')),
    revoked_at timestamptz,
    PRIMARY KEY (workspace_id, project_id, user_id),
    FOREIGN KEY (workspace_id, project_id) REFERENCES team_projects(workspace_id, id),
    FOREIGN KEY (workspace_id, user_id) REFERENCES team_members(workspace_id, user_id)
);

CREATE TABLE team_groups (
    workspace_id uuid NOT NULL REFERENCES team_workspaces(workspace_id),
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 100),
    archived_at timestamptz,
    PRIMARY KEY (workspace_id, id)
);

CREATE UNIQUE INDEX team_active_group_names_idx
    ON team_groups (workspace_id, lower(name)) WHERE archived_at IS NULL;

CREATE TABLE team_group_members (
    workspace_id uuid NOT NULL,
    group_id uuid NOT NULL,
    user_id uuid NOT NULL,
    revoked_at timestamptz,
    PRIMARY KEY (workspace_id, group_id, user_id),
    FOREIGN KEY (workspace_id, group_id) REFERENCES team_groups(workspace_id, id),
    FOREIGN KEY (workspace_id, user_id) REFERENCES team_members(workspace_id, user_id)
);

CREATE TABLE team_group_projects (
    workspace_id uuid NOT NULL,
    group_id uuid NOT NULL,
    project_id uuid NOT NULL,
    revoked_at timestamptz,
    PRIMARY KEY (workspace_id, group_id, project_id),
    FOREIGN KEY (workspace_id, group_id) REFERENCES team_groups(workspace_id, id),
    FOREIGN KEY (workspace_id, project_id) REFERENCES team_projects(workspace_id, id)
);

CREATE INDEX team_group_member_lookup_idx ON team_group_members (workspace_id, user_id, group_id)
    WHERE revoked_at IS NULL;
CREATE INDEX team_group_project_lookup_idx ON team_group_projects (workspace_id, project_id, group_id)
    WHERE revoked_at IS NULL;

CREATE TABLE team_invitations (
    workspace_id uuid NOT NULL,
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    inviter_user_id uuid NOT NULL,
    recipient_issuer text,
    recipient_subject text,
    recipient_email text,
    role text NOT NULL CHECK (role IN ('admin', 'member')),
    token_hash text NOT NULL CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL CHECK (expires_at > created_at),
    accepted_at timestamptz,
    accepted_by_user_id uuid,
    revoked_at timestamptz,
    PRIMARY KEY (workspace_id, id),
    UNIQUE (workspace_id, token_hash),
    CHECK ((recipient_subject IS NOT NULL) <> (recipient_email IS NOT NULL)),
    CHECK (recipient_subject IS NULL OR recipient_issuer IS NOT NULL),
    CHECK ((accepted_at IS NULL) = (accepted_by_user_id IS NULL)),
    FOREIGN KEY (workspace_id, inviter_user_id) REFERENCES team_members(workspace_id, user_id),
    FOREIGN KEY (workspace_id, accepted_by_user_id) REFERENCES team_members(workspace_id, user_id)
);

CREATE TABLE team_bindings (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    sponsor_user_id uuid NOT NULL,
    kind text NOT NULL CHECK (kind IN ('human', 'service')),
    client_registration text NOT NULL CHECK (length(btrim(client_registration)) BETWEEN 1 AND 200),
    audience text NOT NULL DEFAULT 'ninai-team' CHECK (audience = 'ninai-team'),
    token_hash text NOT NULL CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL CHECK (expires_at > created_at),
    revoked_at timestamptz,
    PRIMARY KEY (workspace_id, project_id, id),
    UNIQUE (workspace_id, token_hash),
    FOREIGN KEY (workspace_id, project_id) REFERENCES team_projects(workspace_id, id),
    FOREIGN KEY (workspace_id, sponsor_user_id) REFERENCES team_members(workspace_id, user_id)
);

CREATE INDEX team_binding_sponsor_lookup_idx ON team_bindings (workspace_id, sponsor_user_id)
    WHERE revoked_at IS NULL;

CREATE TABLE team_binding_actions (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    binding_id uuid NOT NULL,
    action text NOT NULL CHECK (action IN ('read', 'propose', 'view-history')),
    revoked_at timestamptz,
    PRIMARY KEY (workspace_id, project_id, binding_id, action),
    FOREIGN KEY (workspace_id, project_id, binding_id) REFERENCES team_bindings(workspace_id, project_id, id)
);

CREATE TABLE team_decisions (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    created_by_user_id uuid NOT NULL,
    visibility text NOT NULL CHECK (visibility IN ('private', 'team')),
    topic text NOT NULL CHECK (length(btrim(topic)) BETWEEN 1 AND 200),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, project_id, id),
    FOREIGN KEY (workspace_id, project_id) REFERENCES team_projects(workspace_id, id),
    FOREIGN KEY (workspace_id, created_by_user_id) REFERENCES team_members(workspace_id, user_id)
);

CREATE INDEX team_decision_topic_idx ON team_decisions (workspace_id, project_id, topic);

CREATE TABLE team_decision_versions (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    decision_id uuid NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    sequence bigint GENERATED ALWAYS AS IDENTITY,
    rule text NOT NULL CHECK (length(btrim(rule)) BETWEEN 1 AND 4000),
    rationale text CHECK (rationale IS NULL OR length(btrim(rationale)) BETWEEN 1 AND 8000),
    scope_paths text[] NOT NULL DEFAULT '{}',
    scope_terms text[] NOT NULL DEFAULT '{}',
    expires_at timestamptz,
    proposed_by_user_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, project_id, decision_id, version),
    FOREIGN KEY (workspace_id, project_id, decision_id) REFERENCES team_decisions(workspace_id, project_id, id),
    FOREIGN KEY (workspace_id, proposed_by_user_id) REFERENCES team_members(workspace_id, user_id),
    CHECK (cardinality(scope_paths) <= 32 AND cardinality(scope_terms) <= 32)
);

CREATE TABLE team_decision_reviewers (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    decision_id uuid NOT NULL,
    user_id uuid NOT NULL,
    revoked_at timestamptz,
    PRIMARY KEY (workspace_id, project_id, decision_id, user_id),
    FOREIGN KEY (workspace_id, project_id, decision_id) REFERENCES team_decisions(workspace_id, project_id, id),
    FOREIGN KEY (workspace_id, user_id) REFERENCES team_members(workspace_id, user_id)
);

CREATE TABLE team_decision_sources (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    decision_id uuid NOT NULL,
    version integer NOT NULL,
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    provider text NOT NULL CHECK (provider IN ('github', 'linear', 'notion')),
    resource_key text NOT NULL CHECK (length(resource_key) BETWEEN 1 AND 512),
    source_url text NOT NULL CHECK (length(source_url) BETWEEN 1 AND 1024),
    expected_fingerprint text CHECK (expected_fingerprint ~ '^[0-9a-f]{64}$'),
    required boolean NOT NULL DEFAULT true,
    optional_basis text,
    PRIMARY KEY (workspace_id, project_id, decision_id, version, id),
    UNIQUE (workspace_id, project_id, decision_id, version, provider, resource_key),
    CHECK ((required AND optional_basis IS NULL) OR
           (NOT required AND optional_basis IS NOT NULL AND length(btrim(optional_basis)) BETWEEN 1 AND 1000)),
    FOREIGN KEY (workspace_id, project_id, decision_id, version)
        REFERENCES team_decision_versions(workspace_id, project_id, decision_id, version)
);

CREATE TABLE team_source_pins (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    decision_id uuid NOT NULL,
    version integer NOT NULL,
    source_id uuid NOT NULL,
    fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (workspace_id, project_id, decision_id, version, source_id),
    FOREIGN KEY (workspace_id, project_id, decision_id, version, source_id)
        REFERENCES team_decision_sources(workspace_id, project_id, decision_id, version, id)
);

CREATE TABLE team_decision_events (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    decision_id uuid NOT NULL,
    version integer NOT NULL,
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    sequence bigint GENERATED ALWAYS AS IDENTITY,
    state text NOT NULL CHECK (state IN ('proposed', 'approved', 'replaced', 'expired', 'retired', 'revoked')),
    actor_user_id uuid,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, project_id, decision_id, version, sequence),
    UNIQUE (workspace_id, id),
    FOREIGN KEY (workspace_id, project_id, decision_id, version)
        REFERENCES team_decision_versions(workspace_id, project_id, decision_id, version),
    FOREIGN KEY (workspace_id, actor_user_id) REFERENCES team_members(workspace_id, user_id),
    CHECK (actor_user_id IS NOT NULL OR state = 'expired')
);

CREATE TABLE team_supersessions (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    decision_id uuid NOT NULL,
    version integer NOT NULL,
    replaces_decision_id uuid NOT NULL,
    replaces_version integer NOT NULL,
    PRIMARY KEY (workspace_id, project_id, decision_id, version),
    UNIQUE (workspace_id, project_id, replaces_decision_id, replaces_version),
    FOREIGN KEY (workspace_id, project_id, decision_id, version)
        REFERENCES team_decision_versions(workspace_id, project_id, decision_id, version),
    FOREIGN KEY (workspace_id, project_id, replaces_decision_id, replaces_version)
        REFERENCES team_decision_versions(workspace_id, project_id, decision_id, version)
);

CREATE TABLE team_audit_events (
    workspace_id uuid NOT NULL REFERENCES team_workspaces(workspace_id),
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    project_id uuid,
    actor_user_id uuid,
    binding_id uuid,
    request_id text NOT NULL CHECK (length(request_id) BETWEEN 1 AND 100),
    action text NOT NULL CHECK (length(action) BETWEEN 1 AND 40),
    outcome text NOT NULL CHECK (length(outcome) BETWEEN 1 AND 40),
    reason text CHECK (reason IS NULL OR length(reason) BETWEEN 1 AND 80),
    recorded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, id),
    UNIQUE (workspace_id, project_id, id),
    FOREIGN KEY (workspace_id, project_id) REFERENCES team_projects(workspace_id, id),
    FOREIGN KEY (workspace_id, actor_user_id) REFERENCES team_members(workspace_id, user_id),
    FOREIGN KEY (workspace_id, project_id, binding_id) REFERENCES team_bindings(workspace_id, project_id, id),
    CHECK (binding_id IS NULL OR project_id IS NOT NULL)
);

CREATE INDEX team_audit_time_idx ON team_audit_events (workspace_id, recorded_at DESC, id DESC);
CREATE INDEX team_audit_actor_action_idx ON team_audit_events
    (workspace_id, actor_user_id, action, outcome, recorded_at DESC) INCLUDE (binding_id);

CREATE TABLE team_audit_items (
    workspace_id uuid NOT NULL,
    event_id uuid NOT NULL,
    project_id uuid NOT NULL,
    decision_id uuid NOT NULL,
    version integer NOT NULL,
    source_status jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(source_status) = 'object'),
    PRIMARY KEY (workspace_id, event_id, project_id, decision_id, version),
    FOREIGN KEY (workspace_id, project_id, event_id) REFERENCES team_audit_events(workspace_id, project_id, id),
    FOREIGN KEY (workspace_id, project_id, decision_id, version)
        REFERENCES team_decision_versions(workspace_id, project_id, decision_id, version)
);

CREATE INDEX team_audit_items_version_idx
    ON team_audit_items (workspace_id, project_id, decision_id, version, event_id);

-- The application uses an unprivileged database identity and sets the tenant
-- only for the current transaction. An absent or reset tenant denies all rows.
CREATE FUNCTION team_current_workspace() RETURNS uuid
    LANGUAGE SQL STABLE PARALLEL SAFE
    SET search_path = pg_catalog
    RETURN nullif(current_setting('ninai.team_workspace_id', true), '')::uuid;

DO $$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'team_workspaces', 'team_members', 'team_projects', 'team_project_members', 'team_groups',
        'team_group_members', 'team_group_projects', 'team_invitations', 'team_bindings',
        'team_binding_actions', 'team_decisions', 'team_decision_versions',
        'team_decision_reviewers', 'team_decision_sources', 'team_source_pins', 'team_decision_events',
        'team_supersessions', 'team_audit_events', 'team_audit_items'
    ] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format(
            'CREATE POLICY team_workspace_scope ON public.%I USING (workspace_id = (SELECT public.team_current_workspace())) WITH CHECK (workspace_id = (SELECT public.team_current_workspace()))',
            table_name
        );
    END LOOP;
END
$$;

-- The runtime role also lacks UPDATE, DELETE and TRUNCATE on these tables.
-- Explicit maintenance privilege is required for deletion after retention.
CREATE FUNCTION team_reject_record_updates() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = pg_catalog
AS $$
BEGIN
    RAISE EXCEPTION 'Team record is immutable' USING ERRCODE = '23514';
END
$$;

DO $$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'team_decisions', 'team_decision_versions', 'team_decision_sources', 'team_source_pins',
        'team_decision_events', 'team_supersessions', 'team_audit_events', 'team_audit_items'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER team_record_immutable BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.team_reject_record_updates()',
            table_name
        );
    END LOOP;
END
$$;

-- Take the same per-decision lock for source attachment and state changes.
-- Once the first event is recorded, the version's source set is closed.
CREATE FUNCTION team_check_version_write() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = pg_catalog
AS $$
DECLARE
    previous_state text;
    previous_sequence bigint;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(
        'ninai-team-version:' || NEW.workspace_id::text || ':' || NEW.project_id::text || ':' || NEW.decision_id::text,
        0
    ));
    SELECT state, sequence INTO previous_state, previous_sequence
    FROM public.team_decision_events
    WHERE workspace_id = NEW.workspace_id AND project_id = NEW.project_id
      AND decision_id = NEW.decision_id AND version = NEW.version
    ORDER BY sequence DESC LIMIT 1;

    IF TG_TABLE_NAME = 'team_decision_sources' THEN
        IF previous_state IS NOT NULL THEN
            RAISE EXCEPTION 'Team decision evidence is immutable' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;

    IF TG_TABLE_NAME = 'team_source_pins' THEN
        IF previous_state IS DISTINCT FROM 'proposed' THEN
            RAISE EXCEPTION 'Team decision evidence can be pinned only during review' USING ERRCODE = '23514';
        END IF;
        IF EXISTS (
            SELECT 1 FROM public.team_decision_sources
            WHERE (workspace_id, project_id, decision_id, version, id) =
                  (NEW.workspace_id, NEW.project_id, NEW.decision_id, NEW.version, NEW.source_id)
              AND expected_fingerprint IS NOT NULL AND expected_fingerprint <> NEW.fingerprint
        ) THEN
            RAISE EXCEPTION 'Team source pin disagrees with stored evidence' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;

    IF NOT (CASE coalesce(previous_state, '')
        WHEN '' THEN NEW.state = 'proposed'
        WHEN 'proposed' THEN NEW.state IN ('approved', 'retired', 'revoked')
        WHEN 'approved' THEN NEW.state IN ('replaced', 'expired', 'retired', 'revoked')
        WHEN 'expired' THEN NEW.state IN ('retired', 'revoked')
        ELSE false
    END) OR NEW.sequence <= previous_sequence THEN
        RAISE EXCEPTION 'Invalid team decision transition' USING ERRCODE = '23514';
    END IF;

    IF NEW.state = 'approved' AND EXISTS (
        SELECT 1 FROM (
            SELECT DISTINCT ON (version) state
            FROM public.team_decision_events
            WHERE workspace_id = NEW.workspace_id AND project_id = NEW.project_id
              AND decision_id = NEW.decision_id AND version <> NEW.version
            ORDER BY version, sequence DESC
        ) AS other_versions WHERE state = 'approved'
    ) THEN
        RAISE EXCEPTION 'Another version of this decision is approved' USING ERRCODE = '23514';
    END IF;

    IF NEW.state = 'approved' AND (
        NOT EXISTS (
            SELECT 1 FROM public.team_decision_sources
            WHERE workspace_id = NEW.workspace_id AND project_id = NEW.project_id
              AND decision_id = NEW.decision_id AND version = NEW.version AND required
        ) OR EXISTS (
            SELECT 1
            FROM public.team_decision_sources AS source
            LEFT JOIN public.team_source_pins AS pin
              ON (pin.workspace_id, pin.project_id, pin.decision_id, pin.version, pin.source_id) =
                 (source.workspace_id, source.project_id, source.decision_id, source.version, source.id)
            WHERE source.workspace_id = NEW.workspace_id AND source.project_id = NEW.project_id
              AND source.decision_id = NEW.decision_id AND source.version = NEW.version AND source.required
              AND coalesce(pin.fingerprint, source.expected_fingerprint) IS NULL
        )
    ) THEN
        RAISE EXCEPTION 'Team decision requires pinned evidence before approval' USING ERRCODE = '23514';
    END IF;
    IF NEW.state = 'replaced' AND NOT EXISTS (
        SELECT 1 FROM public.team_supersessions
        WHERE (workspace_id, project_id, replaces_decision_id, replaces_version) =
              (NEW.workspace_id, NEW.project_id, NEW.decision_id, NEW.version)
    ) THEN
        RAISE EXCEPTION 'Team decision replacement requires an explicit edge' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER team_source_before_lifecycle BEFORE INSERT ON team_decision_sources
    FOR EACH ROW EXECUTE FUNCTION team_check_version_write();
CREATE TRIGGER team_source_pin_during_review BEFORE INSERT ON team_source_pins
    FOR EACH ROW EXECUTE FUNCTION team_check_version_write();
CREATE TRIGGER team_decision_transition BEFORE INSERT ON team_decision_events
    FOR EACH ROW EXECUTE FUNCTION team_check_version_write();

CREATE FUNCTION team_check_supersession() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = pg_catalog
AS $$
BEGIN
    IF (
        SELECT state FROM public.team_decision_events
        WHERE (workspace_id, project_id, decision_id, version) =
              (NEW.workspace_id, NEW.project_id, NEW.decision_id, NEW.version)
        ORDER BY sequence DESC LIMIT 1
    ) IS DISTINCT FROM 'proposed' OR (
        SELECT state FROM public.team_decision_events
        WHERE (workspace_id, project_id, decision_id, version) =
              (NEW.workspace_id, NEW.project_id, NEW.replaces_decision_id, NEW.replaces_version)
        ORDER BY sequence DESC LIMIT 1
    ) IS DISTINCT FROM 'approved' THEN
        RAISE EXCEPTION 'Team decision replacement requires a proposal and an approved predecessor' USING ERRCODE = '23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM public.team_decision_versions AS successor
        JOIN public.team_decision_versions AS predecessor
          ON predecessor.workspace_id = successor.workspace_id
         AND predecessor.project_id = successor.project_id
         AND predecessor.decision_id = NEW.replaces_decision_id
         AND predecessor.version = NEW.replaces_version
         AND predecessor.sequence < successor.sequence
        JOIN public.team_decisions AS successor_decision
          ON successor_decision.workspace_id = successor.workspace_id
         AND successor_decision.project_id = successor.project_id
         AND successor_decision.id = successor.decision_id
        JOIN public.team_decisions AS predecessor_decision
          ON predecessor_decision.workspace_id = predecessor.workspace_id
         AND predecessor_decision.project_id = predecessor.project_id
         AND predecessor_decision.id = predecessor.decision_id
         AND predecessor_decision.topic = successor_decision.topic
         AND predecessor_decision.visibility = successor_decision.visibility
         AND (successor_decision.visibility = 'team' OR
              predecessor_decision.created_by_user_id = successor_decision.created_by_user_id)
        WHERE successor.workspace_id = NEW.workspace_id AND successor.project_id = NEW.project_id
          AND successor.decision_id = NEW.decision_id AND successor.version = NEW.version
    ) THEN
        RAISE EXCEPTION 'Invalid team decision replacement' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER team_supersession_scope BEFORE INSERT ON team_supersessions
    FOR EACH ROW EXECUTE FUNCTION team_check_supersession();

CREATE FUNCTION team_check_committed_supersession() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = pg_catalog
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.team_decision_events
        WHERE (workspace_id, project_id, decision_id, version) =
              (NEW.workspace_id, NEW.project_id, NEW.decision_id, NEW.version) AND state = 'approved'
    ) OR NOT EXISTS (
        SELECT 1 FROM public.team_decision_events
        WHERE (workspace_id, project_id, decision_id, version) =
              (NEW.workspace_id, NEW.project_id, NEW.replaces_decision_id, NEW.replaces_version) AND state = 'replaced'
    ) THEN
        RAISE EXCEPTION 'Team replacement must approve the successor and replace the predecessor atomically' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;

CREATE CONSTRAINT TRIGGER team_supersession_commit AFTER INSERT ON team_supersessions
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION team_check_committed_supersession();
