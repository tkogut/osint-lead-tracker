# om-setup-agent-pipeline — osint-lead-tracker local extension

Repo-local extension of the installed `om-setup-agent-pipeline` skill (the
supported "Per-skill local overrides" mechanism — it extends the upstream skill
and is never overwritten by `npx skills add`).

## Additional step — standard "Deploy to VPS" workflow

After the config, tracker/browser descriptors, labels and project docs are in
place (upstream steps 4–8), add one step:

> If the repository has a `Dockerfile` **and** a `docker-compose.yml`, and
> `.github/workflows/deploy.yml` does **not** exist, propose adding the standard
> automatic-deploy workflow by following the `deploy-to-vps` skill
> (`.agents/skills/deploy-to-vps/SKILL.md`):
> 1. copy `.agents/skills/deploy-to-vps/assets/deploy.yml` to
>    `.github/workflows/deploy.yml`, replacing `__PROJECT__`, `__CONTAINER__`
>    (the `container_name` from `docker-compose.yml`) and
>    `__DEFAULT_DEPLOY_PATH__`;
> 2. print the secret-setup command for the user
>    (`bash .agents/skills/deploy-to-vps/scripts/setup-deploy-secrets.sh <owner>/<repo>`),
>    optionally running it with the user's consent;
> 3. commit it together with the pipeline setup.

Rules for this step:

- **Never create secrets or SSH keys on the user's behalf without explicit
  consent** — the setup script is interactive and confirms each mutation.
- **Never put project-specific values** (host, owner, paths) into the installed
  `om-setup-agent-pipeline` skill; they belong to the `deploy-to-vps` skill and
  the repository variables.
- Skip the step when the repo has no Docker tooling, or when
  `.github/workflows/deploy.yml` already exists (never overwrite an existing
  workflow).
- This step is advisory in `--defaults` mode too: create the workflow file (it is
  safe, non-secret configuration) but only *print* the secret commands.

## Why a local extension rather than editing the upstream skill

`om-setup-agent-pipeline` is installed from the upstream `open-mercato/skills`
collection and is overwritten on upgrade. The deploy convention is
workspace-specific (fixed VPS host, SSH-key flow, Traefik/Docker-Compose stack),
so it is kept in the portable `deploy-to-vps` skill and hooked in here via the
official local-override mechanism.
