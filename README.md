# ArbitrEx — Court of the Internet for Freelance Work

AI-powered freelance dispute resolution built on [GenLayer](https://genlayer.com).

5 independent AI validators act as judges. Graduated verdicts. On-chain case law. No lawyers.

## Live Deployments

| Network | Address |
|---------|---------|
| Bradbury Testnet | `0x06A175AaDDf5b2f198F3Dca36DFA02374c204EAC` |
| Studio | `0xC260c0A68a463Ed9aa82C39D9B1a43F8C0CA2354` |

## Frontend

Live at: **https://arbitrex-app.vercel.app**

## Features

- **Impossible Task Detector** — AI validators assess job feasibility before money locks
- **AI Mediation** — Get a compromise suggestion before filing a formal dispute
- **Court of the Internet** — 5 validators independently judge disputes with graduated verdicts (0/25/50/75/100%)
- **Court of Appeals** — One appeal with stricter evidentiary standard
- **Milestone Verification** — Staged payment releases verified by AI
- **On-Chain Case Law** — Every verdict becomes precedent for future cases
- **Reputation System** — Builds over time, influences future verdicts

## Contract Methods

### Write Methods
| Method | Description |
|--------|-------------|
| `create_job` | Post a job — AI assesses feasibility (Validator Call 1) |
| `accept_job` | Freelancer accepts a job |
| `submit_work` | Freelancer submits completed work |
| `approve_work` | Client approves and releases payment |
| `request_mediation` | AI mediators suggest compromise (Validator Call 2) |
| `file_dispute` | 5 validators issue graduated verdict (Validator Call 3) |
| `appeal_verdict` | Court of Appeals reviews ruling (Validator Call 4) |
| `verify_milestone` | AI verifies milestone completion (Validator Call 5) |

### Read Methods
| Method | Description |
|--------|-------------|
| `get_job` | Get job details |
| `get_dispute` | Get dispute details and verdict |
| `get_reputation` | Get address reputation score |
| `get_case_law` | Get on-chain precedents by category |
| `get_all_jobs` | Get all jobs board |
| `get_all_disputes` | Get all disputes |
| `get_platform_stats` | Get platform statistics |

## AI Consensus Pattern

Uses `gl.eq_principle.prompt_comparative` — the production-recommended pattern for Bradbury:

```python
def assess_job():
    result = gl.nondet.exec_prompt(prompt, response_format='json')
    return json.dumps(result, sort_keys=True)

raw = gl.eq_principle.prompt_comparative(
    assess_job,
    "feasible field must match; clarity_score within 20 points"
)
```

## Tech Stack

- **Contract**: Python Intelligent Contract on GenLayer
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Wallet**: RainbowKit + Wagmi (MetaMask, WalletConnect, Coinbase, Rainbow)
- **Network**: GenLayer Bradbury Testnet (Chain ID: 4221)

## Author

Built by Albert ([@mr_Albert_blaq](https://twitter.com/mr_Albert_blaq)) for the GenLayer Builder Program.
