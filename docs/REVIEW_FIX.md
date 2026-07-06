# Review Fix: URL Fetching Before AI Scoring

## Original Issue

The original `submit_work` scoring flow passed the worker submission to the LLM as prompt text similar to:

```text
Link: {submission_link}
```

That meant the LLM received the URL string, but not the actual page, repository, document, or file content behind that URL.

## Why That Was Wrong

Validator LLMs cannot be assumed to browse a URL just because the URL appears inside a prompt. If the contract asks an LLM to score a submission based only on a link, the model may infer, guess, or over-trust the worker description instead of evaluating the delivered artifact.

For ArbitrEx, that was a material issue because payment scoring should be based on the submitted work content where possible, not only the existence of a URL.

## Actual Fix

Commit `de45b2e` updates `submit_work` so the contract fetches the submitted URL inside the nondeterministic block before calling the scoring LLM:

```python
response = gl.nondet.web.get(submission_link)
```

The fetched response body is decoded and bounded before being included in the prompt.

## Perfected Fix: Render Fallback

The hardened scoring flow still uses `gl.nondet.web.get()` first. It then checks whether the result is weak or unusable:

- HTTP status `>= 400`
- Empty content
- Content shorter than about 300 characters
- Common JavaScript shell indicators such as `You need to enable JavaScript`, `<div id="root">`, `__NEXT_DATA__`, `vite`, or `webpack`

When the initial response looks weak, the contract falls back to:

```python
gl.nondet.web.render(submission_link, mode="text", wait_after_loaded="5s")
```

This improves review quality for Vercel, Netlify, and other JavaScript-heavy submissions where a simple HTTP GET may return only an app shell.

## Prompt Receives Fetched Content

The scoring prompt now contains a dedicated section:

```text
FETCHED CONTENT FROM SUBMISSION URL:
{fetched_content}
```

The prompt also includes fetch status and fetch method so validators can distinguish successful GET fetches, rendered-text fallbacks, and failed fetch attempts.

The fetched content is explicitly labeled as untrusted worker evidence. The prompt instructs the AI not to follow instructions found inside the fetched content and to score only whether the evidence satisfies the job requirements.

## Conservative Scoring On Fetch Failure

If the fetch fails, returns an HTTP error, or produces empty/unreadable content, the prompt instructs the scorer to use a conservative low score and explain the fetch failure. This avoids giving a high score for content the validators did not actually see.

## Later Dispute Flows

After scoring, the contract stores a bounded fetched-content excerpt in `job.fetched_content`.

The following later flows include `job.fetched_content` in their prompts:

- `request_mediation`
- `file_dispute`
- `appeal_verdict`

This keeps later review paths aligned with the actual submission content captured during scoring instead of relying only on `job.work_submission`.

## Redeployment Proof

To be filled after redeployment:

- Contract address: `<TO_BE_UPDATED_AFTER_REDEPLOY>`
- Deployment transaction: `<TO_BE_UPDATED_AFTER_REDEPLOY>`
- Network: GenLayer Bradbury Testnet
- Chain ID: `4221`
- RPC: `https://rpc-bradbury.genlayer.com`
