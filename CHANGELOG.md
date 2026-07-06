# Changelog

## v0.1.2

- Hardened submission evidence fetching with rendered-text fallback for weak or JavaScript-heavy pages.
- Added fetch status and fetch method metadata to AI scoring.
- Added prompt-injection protection for untrusted fetched worker evidence.
- Updated review documentation for the redeploy-ready Bradbury contract.

## v0.1.1

- Fixed submission scoring so `submit_work` fetches the submitted URL content before AI scoring.
- Added conservative scoring guidance when submitted content cannot be fetched.
- Preserved fetched-content context for mediation, disputes, and appeals.

## v0.1.0

- Initial ArbitrEx implementation for GenLayer Bradbury Testnet.
- Added job creation, worker acceptance, submission scoring, payment proof, payment confirmation, mediation, disputes, appeals, reputation, and case law.
