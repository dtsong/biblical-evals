# Architecture Diagrams

This document gives a repo-wide view of how the web app, API, infra, and delivery pipelines fit together.

## 1) Monorepo Component Map

```mermaid
flowchart LR
  subgraph Repo["biblical-evals monorepo"]
    subgraph Web["apps/web - Next.js 14"]
      WApp["app routes and pages"]
      WMid["middleware.ts"]
      WAuth["lib/auth.ts - Auth.js"]
      WToken["api auth token route"]
      WClient["lib/api.ts client"]
      WComp["components"]
    end

    subgraph API["apps/api - FastAPI"]
      ARoutes["api routers"]
      ADep["dependencies/auth.py"]
      AJwt["core/jwt.py"]
      ADb["db models and repository"]
      ARun["runners/litellm_runner.py"]
      AScore["scoring/aggregator.py"]
      AReport["reporting/generator.py"]
      ALoad["loaders config and question"]
    end

    subgraph Content["Runtime Content"]
      QYaml["questions yaml files"]
      CYaml["config yaml files"]
    end

    subgraph Infra["terraform"]
      TFMain["main.tf"]
      TFRun["module cloud_run"]
      TFSql["module cloud_sql"]
      TFSecrets["Secret Manager resources"]
    end

    subgraph Ops["Automation and Tooling"]
      CI[".github/workflows/ci.yml"]
      Deploy[".github/workflows/deploy-api.yml"]
      Setup["scripts/setup-env.sh"]
    end
  end

  WClient --> ARoutes
  WToken --> WClient
  WMid --> WAuth
  WApp --> WComp
  ARoutes --> ADep --> AJwt
  ARoutes --> ADb
  ARoutes --> ARun
  ARoutes --> AScore --> AReport
  ALoad --> ARoutes
  QYaml --> ALoad
  CYaml --> ALoad
  TFMain --> TFRun
  TFMain --> TFSql
  TFMain --> TFSecrets
  CI --> Web
  CI --> API
  CI --> Infra
  Deploy --> TFRun
  Setup --> Web
  Setup --> API
```

## 2) Runtime Request + Auth/Data Flow

```mermaid
sequenceDiagram
  autonumber
  actor U as Reviewer and Admin
  participant V as Vercel apps web
  participant MW as Next Middleware
  participant NA as Auth.js NextAuth
  participant TR as api auth token route
  participant API as FastAPI on Cloud Run
  participant AD as dependencies/auth.py
  participant JWT as core/jwt.py
  participant DB as PostgreSQL on Cloud SQL
  participant LLM as LLM Providers

  U->>V: Open protected page
  V->>MW: Route request
  MW->>NA: Validate session
  alt No session
    MW-->>U: Redirect to /auth/login
  else Session exists
    MW-->>U: Allow route
    V->>TR: Fetch raw JWT cookie token
    TR-->>V: token
    V->>API: Authorization: Bearer <JWT>
    API->>AD: get_current_user dependency
    AD->>JWT: verify_token (HS256, NEXTAUTH_SECRET)
    JWT-->>AD: claims or invalid
    AD->>DB: find/create/update User + access status
    AD-->>API: Current user (or 401/403 ACCESS_PENDING)
    API->>DB: evaluations/responses/scores/reports
    API->>LLM: Run model calls during evaluation runs
    API-->>V: JSON payload
    V-->>U: UI render evaluations review reports
  end
```

## 3) Delivery Pipeline (CI + Deploy)

```mermaid
flowchart TD
  Dev["Developer push to main"] --> GH["GitHub repository"]

  GH --> CI["CI workflow"]
  CI --> CHG["dorny paths filter"]
  CHG -->|api changes| ALint["api-lint ruff check and format check"]
  ALint --> ATest["api-test pytest coverage >= 85%"]
  CHG -->|web changes| WChecks["web checks lint typecheck test build"]
  CHG -->|terraform changes| TFVal["terraform fmt init validate"]

  GH -->|api changes on main| DAPI["Deploy API workflow"]
  DAPI --> Build["Docker buildx build and push"]
  Build --> AR["Artifact Registry"]
  AR --> CloudRun["Cloud Run service biblical-evals-api"]

  GH --> Vercel["Vercel project biblical-evals-web"]
  Vercel --> WebProd["Production web deployment"]
```

## 4) Cloud Infrastructure Topology (Terraform-Managed)

```mermaid
flowchart LR
  subgraph GCP["Google Cloud - trainerlab-prod"]
    AR["Artifact Registry: biblical-evals-api"]
    SM["Secret Manager: NEXTAUTH and provider keys and DB password"]
    SA["Service Account: biblical-evals-api"]
    CR["Cloud Run: biblical-evals-api"]
    SQL["Cloud SQL: biblical_evals"]
    VPC["VPC and subnet from foundation remote state"]
  end

  AR --> CR
  SM --> CR
  SA --> CR
  SA --> SQL
  VPC --> CR
  VPC --> SQL
  CR --> SQL
```
