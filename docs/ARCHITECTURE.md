# ArbitrEx Architecture

## Contract Storage

The GenLayer contract in `contracts/arbitrex.py` stores the core application state:

- Jobs keyed by job ID.
- Disputes keyed by dispute ID.
- Reputation records keyed by participant address.
- Case law keyed by job category.
- Platform counters for jobs, disputes, completed jobs, and total tracked value.

Jobs include client, worker, budget, requirements, submission data, scoring output, fetched-content excerpt, payment state, and status. Disputes include the linked job, filer, grounds, verdict, appeal state, and status.

## Job Lifecycle

1. `create_job` creates a job and asks AI validators to assess feasibility and clarity.
2. `accept_job` assigns the caller as the worker.
3. `submit_work` records the worker submission URL and description.
4. During `submit_work`, the contract fetches public URL content and asks validators to score the actual fetched content against the requirements.
5. The score maps to a payment percentage and payment due value.
6. The client can submit payment proof, request mediation, or file a dispute.
7. The worker can confirm payment receipt or flag payment default after the payment window.
8. Completed and resolved flows update reputation and platform counters.

## Dispute Lifecycle

Disputes start after a job has been scored. Either the client or worker can call `file_dispute` with grounds for review.

The dispute prompt includes job requirements, submission URL, fetched-content excerpt, worker explanation, original score, original reasoning, dispute grounds, and recent precedent from the same category. The AI-assisted verdict returns a worker payment percentage of `0`, `25`, `50`, `75`, or `100`.

After a dispute is resolved, either party can call `appeal_verdict`. Appeals use a stricter standard and can uphold or modify the verdict.

## Reputation System

The contract tracks participant reputation over time. Reputation is updated through completed work, dispute outcomes, and appeal outcomes. The goal is to retain a simple on-chain signal of participant history without making reputation the only determinant of future outcomes.

Reputation data is available through `get_reputation`.

## Case Law / Precedent System

ArbitrEx stores bounded precedent per category in `case_law`. Scoring and dispute flows can reference recent prior cases from the same category.

This creates lightweight on-chain continuity: similar future disputes can see summaries of recent scoring or verdict outcomes without requiring off-chain indexing.

## AI Calls

AI-assisted flows are used for:

- Feasibility and clarity assessment in `create_job`.
- URL fetch, rendered-text fallback, and work scoring in `submit_work`.
- Mediation suggestions in `request_mediation`.
- Formal dispute verdicts in `file_dispute`.
- Appeal review in `appeal_verdict`.

For submission scoring, `submit_work` fetches the submitted URL using `gl.nondet.web.get` before prompting the LLM. If the response is an HTTP error, empty, too short, or looks like a JavaScript application shell, the contract falls back to `gl.nondet.web.render` in text mode. The LLM receives fetched content, fetch status, fetch method, requirements, worker explanation, prior cases, and scoring rules.

## Frontend-To-Contract Interaction

The Next.js frontend connects to the GenLayer Bradbury Testnet using the chain configuration in `src/lib/config.ts`.

Users interact with the contract through wallet-connected actions:

- Clients create jobs, review scores, submit payment proof, request mediation, or file disputes.
- Workers accept jobs, submit public proof-of-work URLs, and participate in disputes or appeals.
- Read views load jobs, disputes, reputation, and platform stats from the contract.

The frontend contract address is configured as:

```text
<TO_BE_UPDATED_AFTER_REDEPLOY>
```
