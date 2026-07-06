# Testing Guide

This repository currently documents manual test flows for the Bradbury testnet prototype. Automated contract integration tests should be added as future work.

## Manual Test Flow

Use the GenLayer Bradbury Testnet:

- RPC: `https://rpc-bradbury.genlayer.com`
- Chain ID: `4221`
- Contract: `<TO_BE_UPDATED_AFTER_REDEPLOY>`

Start the frontend locally:

```bash
npm install
npm run dev
```

Connect a wallet configured for Bradbury and use separate accounts for client and worker when possible.

## `create_job` Test

1. Connect as the client.
2. Create a job with a clear title, category, budget, requirements, and deadline.
3. Confirm the transaction.
4. Verify the job appears in the job list.
5. Open the job details and confirm the feasibility/clarity review fields are populated.

Expected result: the job is created in an open state and includes AI feasibility output.

## `accept_job` Test

1. Switch to a worker wallet.
2. Open the created job.
3. Accept the job.
4. Confirm the transaction.

Expected result: the job worker becomes the connected worker address and the status moves to accepted/in progress.

## `submit_work` Test With A Public GitHub URL

1. Use the worker wallet for the accepted job.
2. Submit a public GitHub URL, such as a repository, pull request, issue, gist, or raw file URL.
3. Include a concise description of the delivered work.
4. Confirm the transaction and wait for scoring.

Expected result: `submit_work` fetches the public URL content before scoring and moves the job to scored state.

## `submit_work` Test With A Vercel/Netlify URL

1. Use the worker wallet for an accepted job.
2. Submit a public Vercel or Netlify URL where a basic HTTP GET may return a JavaScript app shell.
3. Include a concise description of the delivered work.
4. Confirm the transaction and wait for scoring.

Expected result: if the initial GET content is weak, `submit_work` falls back to rendered text with `gl.nondet.web.render(..., mode="text", wait_after_loaded="5s")`. The read output should show useful `fetched_content`, and the scoring reasoning should reflect the rendered page content where available.

## Expected Proof That `fetched_content` Is Used

The deployed contract code stores a bounded excerpt from the fetched or rendered submission content in `job.fetched_content`.

To verify behavior:

1. Submit a URL with distinctive public text in the page or raw file.
2. Read the job after scoring with `get_job`.
3. Confirm the returned job data includes a `fetched_content` value that matches an excerpt from the public URL.
4. Confirm the AI scoring reasoning reflects the submitted content rather than only the worker description.

The scoring prompt contains:

```text
FETCHED CONTENT FROM SUBMISSION URL:
{fetched_content}
```

If the URL cannot be fetched, expected behavior is conservative scoring with reasoning that mentions fetch failure.

## Payment Proof Flow

1. After scoring, review `payment_pct` and `payment_due`.
2. If the client accepts the result, complete payment off-chain or through the agreed testnet flow.
3. Call `submit_payment_proof` from the client wallet with a payment proof reference.
4. Switch to the worker wallet and call `confirm_payment_received`.
5. Confirm the job status and payment confirmation fields update.

Expected result: the contract records payment confirmation and updates completion/reputation state according to the contract logic.

## Dispute Flow

1. After scoring, connect as either the client or worker.
2. File a dispute with clear grounds.
3. Confirm the transaction and wait for the AI-assisted verdict.
4. Read the dispute details.
5. Confirm the verdict percentage, reasoning, and linked job ID are populated.
6. Optionally call `appeal_verdict` once with specific appeal grounds.

Expected result: dispute and appeal prompts include `job.fetched_content`, so later review paths do not rely only on the original submission URL.
