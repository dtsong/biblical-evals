# GCP Migration Board

Tracking migration from temporary `trainerlab-prod` hosting to dedicated `biblical-evals-prod`.

Primary tracking issue: `#2`

## Priority

- Priority: `P0`
- Risk: `High` (infra cutover + data migration)
- External dependency: GCP billing quota/project creation

## Status Board

| Phase | Goal | Status | Exit Criteria |
|---|---|---|---|
| 0 | Readiness and controls | In progress (#3) | Freeze window, owners, go/no-go checklist |
| 1 | Foundation project/network/bootstrap | Blocked (external repo, #4) | `biblical-evals-prod` project + VPC + state bucket live |
| 2 | App terraform migration | Ready to start (#5) | App infra applied in new project with migrated state |
| 3 | CI/CD cutover | Not started (#6) | Deploy workflow publishes to new project |
| 4 | Data and secrets migration | Not started (#7) | DB + secrets migrated and validated |
| 5 | Decommission temporary resources | Not started (#8) | No active dependency on `trainerlab-prod` |

## Task-by-Task Checklist

### Phase 0 - Readiness and controls

- [x] Add migration labels and priority on GitHub issue.
- [x] Publish this runbook/task board in repo docs.
- [x] Create per-phase execution issues (`#3` to `#8`).
- [ ] Assign execution owners for each phase.
- [ ] Define migration freeze window and communication plan.
- [ ] Create go/no-go checklist and rollback owner sign-off.

### Phase 1 - Foundation (`my-gcp-foundation`)

- [ ] Add `google_folder.biblical_evals` (`stages/organization/folders.tf`).
- [ ] Add `google_project.biblical_evals_prod` (`stages/organization/projects.tf`).
- [ ] Add production tag binding (`stages/organization/tags.tf`).
- [ ] Add Cloud Run public access org policy override (`stages/organization/org-policies.tf`).
- [ ] Create `stages/bootstrap-biblical-evals/main.tf` for state bucket.
- [ ] Create `stages/environments/biblical-evals-prod/` (VPC, PSA, subnet `10.2.x.x`).
- [ ] Apply in order: organization -> bootstrap -> environment.
- [ ] Record outputs needed by this repo (project number, VPC, subnet, state bucket).

### Phase 2 - App terraform (`terraform/`)

- [x] Add target tfvars template (`terraform/biblical-evals-prod.tfvars.example`).
- [x] Add local preflight checker (`scripts/migration-preflight.sh`).
- [ ] Update backend bucket to new state bucket.
- [ ] Update remote_state to new foundation outputs.
- [ ] Update `project_id` default to `biblical-evals-prod`.
- [ ] Update `api_image` default to new Artifact Registry path.
- [ ] Apply Cloud SQL settings: `availability_type=REGIONAL`, `point_in_time_recovery=true`, `backup_retention_days=14`.
- [ ] Remove temporary labels/comments related to co-tenancy.
- [ ] Run `terraform init -migrate-state`.
- [ ] Run `terraform plan` and `terraform apply`.

### Phase 3 - CI/CD cutover

- [ ] Update `.github/workflows/deploy-api.yml` `PROJECT_ID`.
- [ ] Update `.github/workflows/deploy-api.yml` `ARTIFACT_REGISTRY`.
- [ ] Update GitHub secret `GCP_PROJECT_NUMBER`.
- [ ] Validate OIDC auth and deployment end-to-end.

### Phase 4 - Data and secrets migration

- [ ] Export source Cloud SQL database.
- [ ] Import into target Cloud SQL instance.
- [ ] Rotate/create secrets in new project's Secret Manager.
- [ ] Run smoke tests for auth/API/reporting and DB writes.
- [ ] Verify data parity checks.

### Phase 5 - Decommission and cleanup

- [ ] Remove old terraform state prefix from old bucket after stabilization.
- [ ] Destroy or manually remove old `biblical-evals-*` resources in `trainerlab-prod`.
- [ ] Verify no trainerlab resource was modified.
- [ ] Remove temporary comments and references to fallback project.
- [ ] Close issue `#2` with migration report.

## Rollback Plan

If cutover fails, rollback in this order:

1. Revert deploy workflow/project target to `trainerlab-prod`.
2. Re-point web/API environment values to previous service URL and secrets.
3. Restore DB from pre-migration export/snapshot.
4. Keep migrated resources isolated for forensic diff before retry.

## Validation Commands

Run after each major phase:

```bash
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform init
terraform -chdir=terraform validate
```

```bash
cd apps/api && uv run pytest -v --cov=src --cov-report=term-missing --cov-fail-under=85
```

```bash
source ~/.nvm/nvm.sh && nvm use default --silent && pnpm --filter @biblical-evals/web test:coverage
```
