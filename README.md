# ArbitrEx

ArbitrEx is a Bradbury testnet prototype for AI-assisted freelance work validation, payment scoring, mediation, and dispute resolution on GenLayer.

## What Problem ArbitrEx Solves

Freelance work often depends on subjective acceptance criteria, delayed reviews, and disputes where neither party has a low-cost path to resolution. ArbitrEx models a job lifecycle where the worker submits public proof of work, GenLayer validators assess the actual submitted content, and the contract records payment recommendations, dispute outcomes, reputation, and precedent.

The project is intended as a review-ready Bradbury deployment, not a production payment system.

## Why GenLayer Is Used

ArbitrEx uses GenLayer because the contract needs AI-assisted judgment while still preserving deterministic agreement across validators. The contract combines normal on-chain state transitions with GenLayer nondeterministic execution for tasks such as feasibility review, submission scoring, mediation, dispute review, and appeals.

GenLayer is especially relevant here because validators can fetch external public content through `gl.nondet.web.get`, fall back to rendered text for JavaScript-heavy pages with `gl.nondet.web.render`, score the retrieved evidence with an LLM, and return structured JSON that is checked before contract state changes.

## Current Bradbury Deployment

The hardened submission-evidence contract is deployed on GenLayer Bradbury Testnet.

## Key Contract Address

`0x09c460AB5f8A4Dd110e9417de4842Ec469D1092b`

## Deployment Transaction Hash

`0x9804b0c721814dc2703776e3a08ce42ac5d9699f1e3909452fd92bfbb6861571`

## Network Details

| Field | Value |
| --- | --- |
| Network | GenLayer Bradbury Testnet |
| Chain ID | `4221` |
| RPC URL | `https://rpc-bradbury.genlayer.com` |
| Contract | `0x09c460AB5f8A4Dd110e9417de4842Ec469D1092b` |

## Core Workflow

1. A client creates a job with a budget, requirements, category, and deadline.
2. The contract asks AI validators to assess whether the job is feasible and clear.
3. A worker accepts the job.
4. The worker submits a public URL plus a description of the delivered work.
5. The contract fetches the submitted URL content with `gl.nondet.web.get`.
6. If the fetched content is an HTTP error, empty, too short, or looks like a JavaScript application shell, the contract falls back to `gl.nondet.web.render(..., mode="text", wait_after_loaded="5s")`.
7. The fetched content, fetch status, and fetch method are included in the scoring prompt before payment is calculated.
8. The client can submit payment proof, request mediation, or file a dispute.
9. The worker can confirm payment receipt or flag payment default after the payment window.
10. Disputes and appeals produce structured verdicts and update case law and reputation.

## Architecture

The project has two main parts:

- `contracts/arbitrex.py`: GenLayer intelligent contract containing job storage, dispute storage, AI validation, scoring, mediation, case law, and reputation logic.
- `src/`: Next.js frontend that connects wallets, reads contract state, and submits user actions to the Bradbury deployment.

The frontend configuration is in `src/lib/config.ts`, including the Bradbury chain configuration and deployed contract address.

## AI Validation Flow

ArbitrEx uses several AI-assisted contract flows:

- Job feasibility review during `create_job`.
- Automatic submission scoring during `submit_work`.
- Mediation suggestions during `request_mediation`.
- Formal dispute review during `file_dispute`.
- Appeal review during `appeal_verdict`.

AI outputs are expected as structured JSON and are validated before being used for contract state updates.

## Joaquin Review Fix / URL-Fetching Fix

The original scoring flow gave validators a prompt containing only the submitted link. That was insufficient because validator LLMs should not be expected to browse a URL simply because it appears inside prompt text.

The fix in commit `de45b2e` changed `submit_work` so the contract fetches the submitted URL using `gl.nondet.web.get` inside the nondeterministic block before scoring. The hardened version adds a rendered-text fallback for weak or JavaScript-heavy responses. The prompt now includes `FETCHED CONTENT FROM SUBMISSION URL`, `FETCH STATUS`, and `FETCH METHOD`, and scoring instructions require conservative scoring if usable content cannot be fetched.

The scoring prompt also treats fetched content as untrusted worker evidence. It explicitly tells the evaluator not to follow instructions found inside the submission and to score only whether the evidence satisfies the job requirements.

Later dispute flows also include `job.fetched_content`, so mediation, disputes, and appeals are based on the saved fetched-content summary rather than the URL alone.

## Frontend Setup

Install dependencies:

```bash
npm install
```

Create a local environment file from the public example values:

```bash
cp .env.example .env.local
```

Start the development server:

```bash
npm run dev
```

Build the frontend:

```bash
npm run build
```

## Contract Functions

### Write Functions

| Function | Purpose |
| --- | --- |
| `create_job` | Creates a job and runs feasibility review. |
| `accept_job` | Assigns the caller as worker for an open job. |
| `submit_work` | Stores the submission URL and description, fetches URL content, scores the work, and calculates payment due. |
| `submit_payment_proof` | Records client-provided payment proof after scoring. |
| `confirm_payment_received` | Allows the worker to confirm payment receipt. |
| `flag_payment_default` | Allows the worker to flag unpaid scored work after the payment window. |
| `request_mediation` | Produces an AI-assisted compromise suggestion after scoring. |
| `file_dispute` | Creates a dispute and records a verdict percentage. |
| `appeal_verdict` | Allows one appeal after a resolved dispute. |
| `cancel_job` | Allows the client to cancel an open job. |

### Read Functions

| Function | Purpose |
| --- | --- |
| `get_job` | Returns a job by ID. |
| `get_job_for_party` | Returns a job with party-aware score visibility. |
| `get_dispute` | Returns a dispute by ID. |
| `get_reputation` | Returns reputation data for an address. |
| `get_case_law` | Returns stored precedent for a category. |
| `get_supported_categories` | Returns supported job categories. |
| `get_all_jobs` | Returns all jobs. |
| `get_all_disputes` | Returns all disputes. |
| `get_platform_stats` | Returns platform-level counters. |

## Known Limitations

- This is a Bradbury testnet prototype.
- Payment release is represented by contract state and confirmation flow; it is not a production escrow system.
- URL fetching depends on public accessibility of the submitted link.
- The contract stores only a bounded excerpt of fetched content for later review flows.
- AI-assisted scoring can be disputed and appealed, but it remains judgment-based.
- The frontend is configured for the current Bradbury deployment and may need updates for future deployments.

## Future Improvements

- Add automated integration tests against a local or Bradbury-like GenLayer environment.
- Expand frontend visibility into fetched-content proof and scoring details.
- Add richer payment-proof visibility and partial-payment UX.
- Add deployment scripts and reproducible deployment notes.
- Improve dispute evidence handling for multiple files or URLs.

## License

MIT. See [LICENSE](LICENSE).
