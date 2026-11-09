# Local project permissions

## Behavior and upgrade

Named local projects have independent Read, Save, and Delete permissions for each assistant. All start off. Reading does not permit writing or deletion. An assistant must specify the project ID when saving or recalling named-project memory. Explaining or deleting by memory ID checks that memory's project permission.

The local `list_projects` assistant tool returns only explicitly granted projects, their IDs, and allowed actions. Assistants can discover the correct ID without exposing the names of unrelated projects. It does not grant access.

Existing memories are preserved as unassigned records. Existing category read grants continue to apply only to unassigned records. The upgrade does not guess which project owns old memories or silently grant write/delete access. Existing assistant `remember` calls now fail with a permission error until the owner explicitly enables Save for the appropriate area or project. Owner actions in the desktop and CLI remain available.

Captured session context also requires Read for its exact project; a broad category grant no longer authorizes session transcripts. Projects created with the CLI use the same repository/path identity as session capture. A project created with only a name in the desktop is a separate manual project; it is not automatically linked to a repository.

New automatic tool-outcome captures use that same repository/path identity and are stored under the matching named project. They are not shared through the broad unassigned category. Previously captured outcomes remain unassigned until an owner explicitly organizes them; their ownership is not inferred during upgrade.

In the desktop app, create a project when adding a memory, select it, then open Connected assistants to enable the actions each assistant needs. The advanced controls manage Save/Delete for existing unassigned areas. Turning off Read prevents future reads; turn off Save and Delete separately to remove those capabilities too.

## CLI example

Create a named project and use the returned ID in subsequent commands:

```sh
ninai project create "Client A" --path /absolute/path/to/client-a
ninai project grant claude-code PROJECT_ID --capability read
ninai project grant claude-code PROJECT_ID --capability write
ninai remember "Deployment needs approval" --project PROJECT_ID
ninai recall "deployment" --client claude-code --project PROJECT_ID
ninai project revoke claude-code PROJECT_ID --capability read
ninai project revoke claude-code PROJECT_ID --capability write
```

For unassigned category records, the existing grant command defaults to Read. Add an action explicitly when needed:

```sh
ninai permission grant claude-code project --capability write
ninai permission revoke claude-code project --capability write
ninai permission list claude-code
```

## Trust boundary

These permissions govern Ninai API calls. The desktop and CLI operate as the local owner. Software with the same operating-system account and file access can read or alter the database directly; the API does not sandbox that software. The database remains unencrypted by Ninai. Sensitivity labels remain informational. Revocation cannot erase information already disclosed to another application/provider. Deletion remains soft deletion.

## Verification

The automated suite includes a two-project store fixture, legacy-schema upgrade, permission filtering before ranking, separate action grants, real stdio MCP requests, desktop bridge controls, and subprocess CLI grant/revoke scenarios. All use disposable synthetic data. These checks do not establish signed installation, clean-machine usability, enterprise readiness, or comparative recall quality.
