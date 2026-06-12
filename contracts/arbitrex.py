# v0.1.0
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass
import json

# ─────────────────────────────────────────────────────────────────────
#  SUPPORTED CATEGORIES
#  Only categories where AI validators can fairly assess text output
# ─────────────────────────────────────────────────────────────────────

SUPPORTED_CATEGORIES = [
    "Web Development",
    "Smart Contract Development",
    "Writing & Content",
    "Data & Analytics",
    "Marketing & SEO",
    "Research & Reports",
]

# ─────────────────────────────────────────────────────────────────────
#  PAYMENT BRACKET CONSTANTS
#  AI score → payment percentage to worker
# ─────────────────────────────────────────────────────────────────────

# Score 85-100 → 100% to worker
# Score 60-84  → 75% to worker
# Score 40-59  → 50% to worker
# Score 20-39  → 25% to worker
# Score 0-19   → 0% to worker (full refund)

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

JOB_OPEN      = "OPEN"
JOB_ACCEPTED  = "ACCEPTED"
JOB_SUBMITTED = "SUBMITTED"
JOB_SCORED    = "SCORED"       # AI has scored, payment verdict issued
JOB_PAID      = "PAID"         # Client confirmed payment sent
JOB_DISPUTED  = "DISPUTED"
JOB_RESOLVED  = "RESOLVED"
JOB_CANCELLED = "CANCELLED"

DISPUTE_RESOLVED = "RESOLVED"
DISPUTE_FINAL    = "FINAL"


# ─────────────────────────────────────────────────────────────────────
#  STORAGE DATACLASSES
# ─────────────────────────────────────────────────────────────────────

@allow_storage
@dataclass
class Job:
    job_id: str
    client: str
    client_wallet: str      # wallet client will pay FROM
    worker: str
    worker_wallet: str      # wallet worker receives payment TO
    title: str
    description: str
    requirements: str       # explicit acceptance criteria
    budget: str             # e.g. "500 GEN"
    category: str
    status: str
    feasibility: str
    feasibility_score: str
    work_submission: str
    submission_description: str   # worker's own description of what they did
    ai_score: str           # 0-100 from validators
    ai_score_reasoning: str
    payment_pct: str        # 0/25/50/75/100 — from score bracket
    payment_due: str        # exact amount client must send e.g. "375 GEN"
    payment_confirmed: str  # "true"/"false" — client confirms they sent it
    mediation_suggestion: str
    milestone_count: str
    milestones_completed: str
    created_at: str


@allow_storage
@dataclass
class Dispute:
    dispute_id: str
    job_id: str
    filer: str
    defendant: str
    grounds: str
    verdict_pct: str
    verdict_reasoning: str
    appeal_verdict_pct: str
    appeal_reasoning: str
    status: str
    category: str


@allow_storage
@dataclass
class Reputation:
    address: str
    jobs_completed: str
    jobs_scored_well: str    # scored 85+
    disputes_won: str
    disputes_lost: str
    total_disputes: str
    payment_defaults: str    # confirmed verdicts where client didn't pay
    score: str


# ─────────────────────────────────────────────────────────────────────
#  CONTRACT
# ─────────────────────────────────────────────────────────────────────

class ArbitrEx(gl.Contract):
    jobs: TreeMap[str, str]
    disputes: TreeMap[str, str]
    reputations: TreeMap[str, str]
    case_law: TreeMap[str, str]
    job_ids: DynArray[str]
    dispute_ids: DynArray[str]
    job_counter: str
    dispute_counter: str
    owner: str

    def __init__(self) -> None:
        self.job_counter = "0"
        self.dispute_counter = "0"
        self.owner = str(gl.message.sender_address)

    # ── Helpers ─────────────────────────────────────────────────────

    def _next_job_id(self) -> str:
        n = int(self.job_counter) + 1
        self.job_counter = str(n)
        return str(n)

    def _next_dispute_id(self) -> str:
        n = int(self.dispute_counter) + 1
        self.dispute_counter = str(n)
        return str(n)

    def _score_to_pct(self, score: int) -> str:
        if score >= 85: return "100"
        if score >= 60: return "75"
        if score >= 40: return "50"
        if score >= 20: return "25"
        return "0"

    def _calculate_payment_due(self, budget: str, pct: str) -> str:
        """Calculate exact payment due based on budget string and percentage."""
        # Extract number from budget string e.g. "500 GEN" -> 500
        try:
            parts = budget.strip().split()
            amount_str = parts[0]
            currency = parts[1] if len(parts) > 1 else "GEN"
            # Handle decimal amounts
            if "." in amount_str:
                whole, frac = amount_str.split(".")
                # Keep 4 decimal places max
                frac = (frac + "0000")[:4]
                amount_cents = int(whole) * 10000 + int(frac)
                pct_int = int(pct)
                due_cents = (amount_cents * pct_int) // 100
                due_whole = due_cents // 10000
                due_frac = due_cents % 10000
                if due_frac == 0:
                    return str(due_whole) + " " + currency
                return str(due_whole) + "." + str(due_frac).rstrip("0") + " " + currency
            else:
                amount = int(amount_str)
                pct_int = int(pct)
                due = (amount * pct_int) // 100
                return str(due) + " " + currency
        except Exception:
            return pct + "% of " + budget

    def _job_from_json(self, raw: str) -> Job:
        d = json.loads(raw)
        return Job(
            job_id=d["job_id"], client=d["client"],
            client_wallet=d.get("client_wallet", d["client"]),
            worker=d["worker"], worker_wallet=d.get("worker_wallet", ""),
            title=d["title"], description=d["description"],
            requirements=d.get("requirements", ""),
            budget=d["budget"], category=d["category"], status=d["status"],
            feasibility=d.get("feasibility", ""), feasibility_score=d.get("feasibility_score", "0"),
            work_submission=d.get("work_submission", ""),
            submission_description=d.get("submission_description", ""),
            ai_score=d.get("ai_score", ""),
            ai_score_reasoning=d.get("ai_score_reasoning", ""),
            payment_pct=d.get("payment_pct", ""),
            payment_due=d.get("payment_due", ""),
            payment_confirmed=d.get("payment_confirmed", "false"),
            mediation_suggestion=d.get("mediation_suggestion", ""),
            milestone_count=d.get("milestone_count", "1"),
            milestones_completed=d.get("milestones_completed", "0"),
            created_at=d.get("created_at", "0"),
        )

    def _job_to_json(self, job: Job) -> str:
        return json.dumps({
            "job_id": job.job_id, "client": job.client,
            "client_wallet": job.client_wallet,
            "worker": job.worker, "worker_wallet": job.worker_wallet,
            "title": job.title, "description": job.description,
            "requirements": job.requirements,
            "budget": job.budget, "category": job.category, "status": job.status,
            "feasibility": job.feasibility, "feasibility_score": job.feasibility_score,
            "work_submission": job.work_submission,
            "submission_description": job.submission_description,
            "ai_score": job.ai_score,
            "ai_score_reasoning": job.ai_score_reasoning,
            "payment_pct": job.payment_pct,
            "payment_due": job.payment_due,
            "payment_confirmed": job.payment_confirmed,
            "mediation_suggestion": job.mediation_suggestion,
            "milestone_count": job.milestone_count,
            "milestones_completed": job.milestones_completed,
            "created_at": job.created_at,
        }, sort_keys=True)

    def _dispute_from_json(self, raw: str) -> Dispute:
        d = json.loads(raw)
        return Dispute(
            dispute_id=d["dispute_id"], job_id=d["job_id"],
            filer=d["filer"], defendant=d["defendant"],
            grounds=d.get("grounds", ""),
            verdict_pct=d.get("verdict_pct", ""),
            verdict_reasoning=d.get("verdict_reasoning", ""),
            appeal_verdict_pct=d.get("appeal_verdict_pct", ""),
            appeal_reasoning=d.get("appeal_reasoning", ""),
            status=d["status"], category=d.get("category", ""),
        )

    def _dispute_to_json(self, dispute: Dispute) -> str:
        return json.dumps({
            "dispute_id": dispute.dispute_id, "job_id": dispute.job_id,
            "filer": dispute.filer, "defendant": dispute.defendant,
            "grounds": dispute.grounds,
            "verdict_pct": dispute.verdict_pct,
            "verdict_reasoning": dispute.verdict_reasoning,
            "appeal_verdict_pct": dispute.appeal_verdict_pct,
            "appeal_reasoning": dispute.appeal_reasoning,
            "status": dispute.status, "category": dispute.category,
        }, sort_keys=True)

    def _get_rep(self, addr: str) -> Reputation:
        raw = self.reputations.get(addr, None)
        if raw is None:
            return Reputation(address=addr, jobs_completed="0", jobs_scored_well="0",
                              disputes_won="0", disputes_lost="0",
                              total_disputes="0", payment_defaults="0", score="50")
        d = json.loads(raw)
        return Reputation(
            address=d["address"], jobs_completed=d["jobs_completed"],
            jobs_scored_well=d.get("jobs_scored_well", "0"),
            disputes_won=d["disputes_won"], disputes_lost=d["disputes_lost"],
            total_disputes=d["total_disputes"],
            payment_defaults=d.get("payment_defaults", "0"),
            score=d["score"],
        )

    def _save_rep(self, rep: Reputation) -> None:
        self.reputations[rep.address] = json.dumps({
            "address": rep.address, "jobs_completed": rep.jobs_completed,
            "jobs_scored_well": rep.jobs_scored_well,
            "disputes_won": rep.disputes_won, "disputes_lost": rep.disputes_lost,
            "total_disputes": rep.total_disputes,
            "payment_defaults": rep.payment_defaults,
            "score": rep.score,
        }, sort_keys=True)

    def _clamp_score(self, n: int) -> str:
        if n < 0: return "0"
        if n > 100: return "100"
        return str(n)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 1 — create_job
    #  AI: Impossible Task Detector + Category Validator
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def create_job(
        self,
        title: str,
        description: str,
        requirements: str,
        budget: str,
        category: str,
        milestone_count: str,
    ) -> str:
        """
        Post a job. Only supported categories allowed.
        AI validates feasibility and clarity of requirements.
        Returns job ID.
        """
        caller = str(gl.message.sender_address)

        # Validate category
        if category not in SUPPORTED_CATEGORIES:
            raise Exception(
                f"Category '{category}' is not supported. Supported: {', '.join(SUPPORTED_CATEGORIES)}"
            )

        job_id = self._next_job_id()

        prompt = f"""Evaluate this freelance job for an AI-judged platform.
Title: {title}
Description: {description}
Requirements: {requirements}
Budget: {budget}
Category: {category}

Is it feasible? Are the requirements specific enough for AI validators to objectively score the deliverable?
Respond ONLY with JSON:
{{"feasible": true or false, "feasibility_score": <0-100>, "reasoning": "<one sentence>", "recommendation": "PROCEED" or "REVIEW" or "REJECT"}}"""

        def leader_fn():
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            return json.dumps(result, sort_keys=True)

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my_result = leader_fn()
            try:
                leader_data = json.loads(leaders_res.calldata)
                my_data = json.loads(my_result)
                if leader_data["feasible"] != my_data["feasible"]:
                    return False
                score_diff = abs(int(leader_data["feasibility_score"]) - int(my_data["feasibility_score"]))
                return score_diff <= 20
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        ai = json.loads(raw)

        feasible_str = "FEASIBLE" if ai.get("feasible", True) else "INFEASIBLE"
        score_str = str(ai.get("feasibility_score", 70))

        job = Job(
            job_id=job_id, client=caller, client_wallet=caller,
            worker=ZERO_ADDRESS, worker_wallet="",
            title=title, description=description, requirements=requirements,
            budget=budget, category=category, status=JOB_OPEN,
            feasibility=feasible_str, feasibility_score=score_str,
            work_submission="", submission_description="",
            ai_score="", ai_score_reasoning="",
            payment_pct="", payment_due="",
            payment_confirmed="false", mediation_suggestion="",
            milestone_count=milestone_count, milestones_completed="0",
            created_at="0",
        )

        self.jobs[job_id] = self._job_to_json(job)
        self.job_ids.append(job_id)

        # Case law entry
        existing_raw = self.case_law.get(category, "[]")
        existing = json.loads(existing_raw)
        existing.append({"type": "feasibility", "job_id": job_id,
                         "verdict": feasible_str, "score": score_str})
        if len(existing) > 10:
            existing = existing[-10:]
        self.case_law[category] = json.dumps(existing, sort_keys=True)

        return job_id

    # ════════════════════════════════════════════════════════════════
    #  WRITE 2 — accept_job
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def accept_job(self, job_id: str, worker_wallet: str) -> None:
        """
        Freelancer accepts a job.
        worker_wallet: address where payment will be sent after AI scoring.
        """
        caller = str(gl.message.sender_address)
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if job.status != JOB_OPEN:
            raise Exception("Job is not open")
        if job.client == caller:
            raise Exception("Client cannot accept their own job")

        job.worker = caller
        job.worker_wallet = worker_wallet if worker_wallet else caller
        job.status = JOB_ACCEPTED
        self.jobs[job_id] = self._job_to_json(job)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 3 — submit_work
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def submit_work(
        self,
        job_id: str,
        submission_link: str,
        submission_description: str,
    ) -> None:
        """
        Worker submits completed work.
        submission_link: URL to the deliverable (GitHub, Google Doc, deployed URL etc.)
        submission_description: worker's own explanation of what was done and how requirements were met.
        """
        caller = str(gl.message.sender_address)
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if job.worker != caller:
            raise Exception("Only the assigned worker can submit work")
        if job.status != JOB_ACCEPTED:
            raise Exception("Job must be ACCEPTED before submitting work")
        if not submission_link:
            raise Exception("Submission link is required")
        if not submission_description:
            raise Exception("Submission description is required — explain how you met the requirements")

        job.work_submission = submission_link
        job.submission_description = submission_description
        job.status = JOB_SUBMITTED
        self.jobs[job_id] = self._job_to_json(job)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 4 — score_work  ← REPLACES approve/decline
    #  AI Validators read brief + submission → score 0-100 → payment verdict
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def score_work(self, job_id: str) -> str:
        """
        Either party (or anyone) can trigger AI scoring after work is submitted.
        5 validators independently score the submission against the brief.
        Score → payment bracket → binding on-chain payment verdict.
        Returns the score as a string.
        """
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if job.status != JOB_SUBMITTED:
            raise Exception("Work must be submitted before scoring")

        precedent_raw = self.case_law.get(job.category, "[]")
        precedents = json.loads(precedent_raw)
        precedent_str = ""
        for p in precedents[-3:]:
            if p.get("type") == "scoring":
                precedent_str += f"- Similar job scored {p.get('score','?')}/100: {p.get('summary','')}\n"

        prompt = f"""You are an impartial AI judge scoring freelance work for payment release.

=== JOB BRIEF ===
Title: {job.title}
Description: {job.description}
Requirements: {job.requirements}
Budget: {job.budget}
Category: {job.category}

=== SUBMITTED WORK ===
Link: {job.work_submission}
Worker's Description: {job.submission_description}

=== SCORING RUBRIC ===
Score the work 0-100 based on:
- Does the submission address all stated requirements? (40 points)
- Is the quality appropriate for the budget and scope? (30 points)
- Is the submission complete with no major gaps? (20 points)
- Is the submission clearly delivered and accessible? (10 points)

Payment brackets:
85-100 → full payment | 60-84 → 75% | 40-59 → 50% | 20-39 → 25% | 0-19 → no payment

Prior cases in {job.category}: {precedent_str if precedent_str else "None"}

Respond ONLY with JSON:
{{"score": <0-100>, "reasoning": "<3-4 sentence detailed explanation>", "requirements_met": "<which requirements were met>", "gaps": "<what was missing or incomplete>", "payment_bracket": "100% or 75% or 50% or 25% or 0%"}}"""

        def leader_fn():
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            return json.dumps(result, sort_keys=True)

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my_result = leader_fn()
            try:
                leader_data = json.loads(leaders_res.calldata)
                my_data = json.loads(my_result)
                leader_score = int(leader_data.get("score", -1))
                my_score = int(my_data.get("score", -2))
                if not (0 <= leader_score <= 100):
                    return False
                # Validators must agree within 15 points
                return abs(leader_score - my_score) <= 15
            except Exception:
                return False

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        ai = json.loads(raw_result)

        score = int(ai.get("score", 50))
        reasoning = ai.get("reasoning", "")
        requirements_met = ai.get("requirements_met", "")
        gaps = ai.get("gaps", "")

        # Full reasoning stored on-chain
        full_reasoning = reasoning
        if requirements_met:
            full_reasoning += " | Met: " + requirements_met
        if gaps:
            full_reasoning += " | Gaps: " + gaps

        payment_pct = self._score_to_pct(score)
        payment_due = self._calculate_payment_due(job.budget, payment_pct)

        job.ai_score = str(score)
        job.ai_score_reasoning = full_reasoning
        job.payment_pct = payment_pct
        job.payment_due = payment_due
        job.status = JOB_SCORED
        self.jobs[job_id] = self._job_to_json(job)

        # Update worker reputation based on score
        worker_rep = self._get_rep(job.worker)
        if score >= 85:
            worker_rep.jobs_scored_well = str(int(worker_rep.jobs_scored_well) + 1)
            worker_rep.score = self._clamp_score(int(worker_rep.score) + 5)
        elif score >= 60:
            worker_rep.score = self._clamp_score(int(worker_rep.score) + 2)
        elif score < 40:
            worker_rep.score = self._clamp_score(int(worker_rep.score) - 5)
        self._save_rep(worker_rep)

        # Case law entry
        existing_raw = self.case_law.get(job.category, "[]")
        existing = json.loads(existing_raw)
        existing.append({
            "type": "scoring",
            "job_id": job_id,
            "score": str(score),
            "payment_pct": payment_pct,
            "summary": reasoning[:100] if reasoning else "",
            "category": job.category,
        })
        if len(existing) > 10:
            existing = existing[-10:]
        self.case_law[job.category] = json.dumps(existing, sort_keys=True)

        return str(score)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 5 — confirm_payment
    #  Client confirms they sent payment to worker's wallet
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def confirm_payment(self, job_id: str) -> None:
        """
        Client confirms they sent the payment_due amount to the worker's wallet.
        This is the final step — recorded permanently on-chain.
        """
        caller = str(gl.message.sender_address)
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if job.client != caller:
            raise Exception("Only the client can confirm payment")
        if job.status != JOB_SCORED:
            raise Exception("Work must be scored before confirming payment")
        if job.payment_pct == "0":
            raise Exception("No payment is due — AI score was below 20")

        job.payment_confirmed = "true"
        job.status = JOB_PAID
        self.jobs[job_id] = self._job_to_json(job)

        # Update reputations
        worker_rep = self._get_rep(job.worker)
        worker_rep.jobs_completed = str(int(worker_rep.jobs_completed) + 1)
        self._save_rep(worker_rep)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 6 — flag_payment_default
    #  Worker flags that client didn't pay after a binding verdict
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def flag_payment_default(self, job_id: str) -> None:
        """
        Worker flags that the client has not paid after a SCORED verdict.
        Records a permanent payment default against the client's address.
        Anyone can verify this on-chain.
        """
        caller = str(gl.message.sender_address)
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if job.worker != caller:
            raise Exception("Only the worker can flag a payment default")
        if job.status != JOB_SCORED:
            raise Exception("Job must be in SCORED status")
        if job.payment_pct == "0":
            raise Exception("No payment was due")

        # Record payment default against client's reputation
        client_rep = self._get_rep(job.client)
        client_rep.payment_defaults = str(int(client_rep.payment_defaults) + 1)
        client_rep.score = self._clamp_score(int(client_rep.score) - 20)
        self._save_rep(client_rep)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 7 — cancel_job
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def cancel_job(self, job_id: str) -> None:
        """Client cancels an OPEN job before anyone accepts."""
        caller = str(gl.message.sender_address)
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if job.client != caller:
            raise Exception("Only the client can cancel")
        if job.status != JOB_OPEN:
            raise Exception("Can only cancel OPEN jobs")
        job.status = JOB_CANCELLED
        self.jobs[job_id] = self._job_to_json(job)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 8 — request_mediation
    #  AI Mediator — before escalating to full dispute
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def request_mediation(self, job_id: str, your_position: str) -> None:
        """Either party requests AI mediation before filing a formal dispute."""
        caller = str(gl.message.sender_address)
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if caller != job.client and caller != job.worker:
            raise Exception("Only job parties can request mediation")
        if job.status not in [JOB_SUBMITTED, JOB_SCORED]:
            raise Exception("Mediation only available after work is submitted")

        prompt = f"""Mediate this freelance dispute.
Job: {job.title} | Budget: {job.budget}
Requirements: {job.requirements}
Work submitted: {job.work_submission}
Worker description: {job.submission_description}
AI Score: {job.ai_score if job.ai_score else "Not yet scored"}
Party position: {your_position}

Suggest a fair compromise.
Respond ONLY with JSON:
{{"compromise_suggestion": "<compromise>", "recommended_split": "<% to worker>", "confidence": <0-100>, "key_issues": "<issues>"}}"""

        def leader_fn():
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            return json.dumps(result, sort_keys=True)

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            try:
                leader_data = json.loads(leaders_res.calldata)
                return len(leader_data.get("compromise_suggestion", "")) > 20
            except Exception:
                return False

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        ai = json.loads(raw_result)
        job.mediation_suggestion = (
            ai.get("compromise_suggestion", "") +
            " | Split: " + ai.get("recommended_split", "") +
            " | Issues: " + ai.get("key_issues", "")
        )
        self.jobs[job_id] = self._job_to_json(job)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 9 — file_dispute
    #  Full Court of the Internet — when parties disagree with AI score
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def file_dispute(self, job_id: str, grounds: str) -> str:
        """
        File a formal dispute against the AI scoring verdict.
        Either party can dispute if they believe the score was wrong.
        5 validators re-examine everything and issue a new verdict.
        """
        caller = str(gl.message.sender_address)
        raw_job = self.jobs.get(job_id, None)
        if raw_job is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw_job)
        if caller != job.client and caller != job.worker:
            raise Exception("Only job parties can file a dispute")
        if job.status != JOB_SCORED:
            raise Exception("Can only dispute after work has been scored")

        dispute_id = self._next_dispute_id()

        precedent_raw = self.case_law.get(job.category, "[]")
        precedents = json.loads(precedent_raw)
        precedent_str = ""
        for p in precedents[-3:]:
            if p.get("type") == "dispute":
                precedent_str += f"- {job.category}: {p.get('verdict_pct','?')}% to worker.\n"

        prompt = f"""Review this freelance dispute. The original AI score is being contested.
Job: {job.title} | Budget: {job.budget}
Requirements: {job.requirements}
Work submitted: {job.work_submission}
Worker description: {job.submission_description}
Original AI score: {job.ai_score}/100 | Original reasoning: {job.ai_score_reasoning}
Dispute grounds: {grounds}
Prior cases: {precedent_str if precedent_str else "None"}

Issue a final payment verdict (% to worker): 0, 25, 50, 75, or 100.
Respond ONLY with JSON:
{{"verdict_pct": <0|25|50|75|100>, "reasoning": "<2-3 sentences>", "key_finding": "<1 sentence>", "confidence": <0-100>}}"""

        def leader_fn():
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            return json.dumps(result, sort_keys=True)

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my_result = leader_fn()
            try:
                leader_data = json.loads(leaders_res.calldata)
                my_data = json.loads(my_result)
                leader_pct = int(leader_data.get("verdict_pct", -1))
                my_pct = int(my_data.get("verdict_pct", -2))
                if leader_pct not in [0, 25, 50, 75, 100]:
                    return False
                return abs(leader_pct - my_pct) <= 25
            except Exception:
                return False

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        ai = json.loads(raw_result)

        verdict_pct = str(ai.get("verdict_pct", 50))
        reasoning = ai.get("reasoning", "")
        key_finding = ai.get("key_finding", "")

        # Update payment due based on new verdict
        payment_due = self._calculate_payment_due(job.budget, verdict_pct)
        job.payment_pct = verdict_pct
        job.payment_due = payment_due
        job.status = JOB_RESOLVED
        self.jobs[job_id] = self._job_to_json(job)

        dispute = Dispute(
            dispute_id=dispute_id, job_id=job_id,
            filer=caller,
            defendant=job.worker if caller == job.client else job.client,
            grounds=grounds,
            verdict_pct=verdict_pct, verdict_reasoning=reasoning,
            appeal_verdict_pct="", appeal_reasoning="",
            status=DISPUTE_RESOLVED, category=job.category,
        )
        self.disputes[dispute_id] = self._dispute_to_json(dispute)
        self.dispute_ids.append(dispute_id)

        # Update reputations
        worker_rep = self._get_rep(job.worker)
        client_rep = self._get_rep(job.client)
        worker_rep.total_disputes = str(int(worker_rep.total_disputes) + 1)
        client_rep.total_disputes = str(int(client_rep.total_disputes) + 1)
        v = int(verdict_pct)
        if v >= 75:
            worker_rep.disputes_won = str(int(worker_rep.disputes_won) + 1)
            worker_rep.score = self._clamp_score(int(worker_rep.score) + 3)
            client_rep.disputes_lost = str(int(client_rep.disputes_lost) + 1)
            client_rep.score = self._clamp_score(int(client_rep.score) - 2)
        elif v <= 25:
            client_rep.disputes_won = str(int(client_rep.disputes_won) + 1)
            client_rep.score = self._clamp_score(int(client_rep.score) + 3)
            worker_rep.disputes_lost = str(int(worker_rep.disputes_lost) + 1)
            worker_rep.score = self._clamp_score(int(worker_rep.score) - 5)
        self._save_rep(worker_rep)
        self._save_rep(client_rep)

        # Case law
        existing_raw = self.case_law.get(job.category, "[]")
        existing = json.loads(existing_raw)
        existing.append({"type": "dispute", "dispute_id": dispute_id,
                         "verdict_pct": verdict_pct, "summary": key_finding,
                         "category": job.category})
        if len(existing) > 10:
            existing = existing[-10:]
        self.case_law[job.category] = json.dumps(existing, sort_keys=True)

        return dispute_id

    # ════════════════════════════════════════════════════════════════
    #  WRITE 10 — appeal_verdict
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def appeal_verdict(self, dispute_id: str, appeal_grounds: str) -> None:
        """Appeal a dispute verdict. Stricter standard — final."""
        caller = str(gl.message.sender_address)
        raw_dispute = self.disputes.get(dispute_id, None)
        if raw_dispute is None:
            raise Exception("Dispute not found")
        dispute = self._dispute_from_json(raw_dispute)
        if dispute.status != DISPUTE_RESOLVED:
            raise Exception("Only RESOLVED disputes can be appealed")

        raw_job = self.jobs.get(dispute.job_id, None)
        if raw_job is None:
            raise Exception("Associated job not found")
        job = self._job_from_json(raw_job)
        if caller != job.client and caller != job.worker:
            raise Exception("Only job parties can appeal")

        prompt = f"""Review this freelance dispute appeal. Strict standard.
Job: {job.title} | Budget: {job.budget}
Requirements: {job.requirements}
Work: {job.work_submission} | Worker description: {job.submission_description}
Original AI score: {job.ai_score}/100
Dispute verdict: {dispute.verdict_pct}% to worker | Reasoning: {dispute.verdict_reasoning}
Appeal grounds: {appeal_grounds}

Overturn only on clear error or new material evidence.
Respond ONLY with JSON:
{{"appeal_verdict_pct": <0|25|50|75|100>, "upheld_original": true or false, "reasoning": "<2-3 sentences>", "verdict_change": "Upheld or Partially Modified or Overturned"}}"""

        def leader_fn():
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            return json.dumps(result, sort_keys=True)

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my_result = leader_fn()
            try:
                leader_data = json.loads(leaders_res.calldata)
                my_data = json.loads(my_result)
                leader_pct = int(leader_data.get("appeal_verdict_pct", -1))
                my_pct = int(my_data.get("appeal_verdict_pct", -2))
                if leader_pct not in [0, 25, 50, 75, 100]:
                    return False
                return abs(leader_pct - my_pct) <= 25
            except Exception:
                return False

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        ai = json.loads(raw_result)

        appeal_pct = str(ai.get("appeal_verdict_pct", dispute.verdict_pct))
        appeal_reasoning = ai.get("reasoning", "")

        # Update payment due if appeal changes verdict
        if appeal_pct != dispute.verdict_pct:
            payment_due = self._calculate_payment_due(job.budget, appeal_pct)
            job.payment_pct = appeal_pct
            job.payment_due = payment_due
            self.jobs[dispute.job_id] = self._job_to_json(job)

        dispute.appeal_verdict_pct = appeal_pct
        dispute.appeal_reasoning = appeal_reasoning
        dispute.status = DISPUTE_FINAL
        self.disputes[dispute_id] = self._dispute_to_json(dispute)

    # ════════════════════════════════════════════════════════════════
    #  READ METHODS
    # ════════════════════════════════════════════════════════════════

    @gl.public.view
    def get_job(self, job_id: str) -> str:
        raw = self.jobs.get(job_id, None)
        return raw if raw is not None else json.dumps({"error": "Job not found"})

    @gl.public.view
    def get_dispute(self, dispute_id: str) -> str:
        raw = self.disputes.get(dispute_id, None)
        return raw if raw is not None else json.dumps({"error": "Dispute not found"})

    @gl.public.view
    def get_reputation(self, address: str) -> str:
        raw = self.reputations.get(address, None)
        if raw is None:
            return json.dumps({"address": address, "jobs_completed": "0",
                               "jobs_scored_well": "0", "disputes_won": "0",
                               "disputes_lost": "0", "total_disputes": "0",
                               "payment_defaults": "0", "score": "50"})
        return raw

    @gl.public.view
    def get_case_law(self, category: str) -> str:
        return self.case_law.get(category, "[]")

    @gl.public.view
    def get_supported_categories(self) -> str:
        return json.dumps(SUPPORTED_CATEGORIES)

    @gl.public.view
    def get_all_jobs(self) -> str:
        result = []
        for jid in self.job_ids:
            raw = self.jobs.get(jid, None)
            if raw is not None:
                result.append(json.loads(raw))
        return json.dumps(result)

    @gl.public.view
    def get_all_disputes(self) -> str:
        result = []
        for did in self.dispute_ids:
            raw = self.disputes.get(did, None)
            if raw is not None:
                result.append(json.loads(raw))
        return json.dumps(result)

    @gl.public.view
    def get_platform_stats(self) -> str:
        total_jobs = int(self.job_counter)
        total_disputes = int(self.dispute_counter)
        open_jobs = 0
        completed_jobs = 0
        scored_jobs = 0
        for jid in self.job_ids:
            raw = self.jobs.get(jid, None)
            if raw is not None:
                d = json.loads(raw)
                s = d.get("status", "")
                if s == JOB_OPEN:
                    open_jobs += 1
                elif s == JOB_PAID:
                    completed_jobs += 1
                elif s == JOB_SCORED:
                    scored_jobs += 1
        return json.dumps({
            "total_jobs": str(total_jobs),
            "total_disputes": str(total_disputes),
            "open_jobs": str(open_jobs),
            "completed_jobs": str(completed_jobs),
            "scored_jobs": str(scored_jobs),
        }, sort_keys=True)
