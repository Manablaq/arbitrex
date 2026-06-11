# v0.1.0
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass
import json

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

MIN_PAYMENT_GEN = "0.0001"
MAX_PAYMENT_GEN = "10000000"

JOB_OPEN       = "OPEN"
JOB_ACCEPTED   = "ACCEPTED"
JOB_SUBMITTED  = "SUBMITTED"
JOB_COMPLETED  = "COMPLETED"
JOB_RESOLVED   = "RESOLVED"
JOB_CANCELLED  = "CANCELLED"

DISPUTE_RESOLVED = "RESOLVED"
DISPUTE_FINAL    = "FINAL"


@allow_storage
@dataclass
class Job:
    job_id: str
    client: str
    worker: str
    title: str
    description: str
    budget_display: str   # e.g. "50 GEN" — informational
    category: str
    status: str
    feasibility: str
    feasibility_score: str
    created_at: str
    accepted_at: str
    submitted_at: str
    completed_at: str
    work_submission: str
    mediation_suggestion: str
    milestone_count: str
    milestones_completed: str
    payment_released: str
    worker_wallet: str


@allow_storage
@dataclass
class Dispute:
    dispute_id: str
    job_id: str
    filer: str
    defendant: str
    client_evidence: str
    worker_evidence: str
    verdict_pct: str
    verdict_reasoning: str
    appeal_verdict_pct: str
    appeal_reasoning: str
    status: str
    created_at: str
    resolved_at: str
    category: str


@allow_storage
@dataclass
class Reputation:
    address: str
    jobs_completed: str
    disputes_won: str
    disputes_lost: str
    total_disputes: str
    score: str


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

    def _next_job_id(self) -> str:
        n = int(self.job_counter) + 1
        self.job_counter = str(n)
        return str(n)

    def _next_dispute_id(self) -> str:
        n = int(self.dispute_counter) + 1
        self.dispute_counter = str(n)
        return str(n)

    def _job_from_json(self, raw: str) -> Job:
        d = json.loads(raw)
        return Job(
            job_id=d["job_id"], client=d["client"], worker=d["worker"],
            title=d["title"], description=d["description"],
            budget_display=d["budget_display"],
            category=d["category"], status=d["status"],
            feasibility=d["feasibility"], feasibility_score=d["feasibility_score"],
            created_at=d["created_at"], accepted_at=d["accepted_at"],
            submitted_at=d["submitted_at"], completed_at=d["completed_at"],
            work_submission=d["work_submission"],
            mediation_suggestion=d["mediation_suggestion"],
            milestone_count=d["milestone_count"],
            milestones_completed=d["milestones_completed"],
            payment_released=d.get("payment_released", "false"),
            worker_wallet=d.get("worker_wallet", ""),
        )

    def _job_to_json(self, job: Job) -> str:
        return json.dumps({
            "job_id": job.job_id, "client": job.client, "worker": job.worker,
            "title": job.title, "description": job.description,
            "budget_display": job.budget_display,
            "category": job.category, "status": job.status,
            "feasibility": job.feasibility, "feasibility_score": job.feasibility_score,
            "created_at": job.created_at, "accepted_at": job.accepted_at,
            "submitted_at": job.submitted_at, "completed_at": job.completed_at,
            "work_submission": job.work_submission,
            "mediation_suggestion": job.mediation_suggestion,
            "milestone_count": job.milestone_count,
            "milestones_completed": job.milestones_completed,
            "payment_released": job.payment_released,
            "worker_wallet": job.worker_wallet,
        }, sort_keys=True)

    def _dispute_from_json(self, raw: str) -> Dispute:
        d = json.loads(raw)
        return Dispute(
            dispute_id=d["dispute_id"], job_id=d["job_id"],
            filer=d["filer"], defendant=d["defendant"],
            client_evidence=d["client_evidence"], worker_evidence=d["worker_evidence"],
            verdict_pct=d["verdict_pct"], verdict_reasoning=d["verdict_reasoning"],
            appeal_verdict_pct=d["appeal_verdict_pct"], appeal_reasoning=d["appeal_reasoning"],
            status=d["status"], created_at=d["created_at"],
            resolved_at=d["resolved_at"], category=d["category"],
        )

    def _dispute_to_json(self, dispute: Dispute) -> str:
        return json.dumps({
            "dispute_id": dispute.dispute_id, "job_id": dispute.job_id,
            "filer": dispute.filer, "defendant": dispute.defendant,
            "client_evidence": dispute.client_evidence, "worker_evidence": dispute.worker_evidence,
            "verdict_pct": dispute.verdict_pct, "verdict_reasoning": dispute.verdict_reasoning,
            "appeal_verdict_pct": dispute.appeal_verdict_pct, "appeal_reasoning": dispute.appeal_reasoning,
            "status": dispute.status, "created_at": dispute.created_at,
            "resolved_at": dispute.resolved_at, "category": dispute.category,
        }, sort_keys=True)

    def _get_rep(self, addr: str) -> Reputation:
        raw = self.reputations.get(addr, None)
        if raw is None:
            return Reputation(address=addr, jobs_completed="0", disputes_won="0",
                              disputes_lost="0", total_disputes="0", score="50")
        d = json.loads(raw)
        return Reputation(address=d["address"], jobs_completed=d["jobs_completed"],
                          disputes_won=d["disputes_won"], disputes_lost=d["disputes_lost"],
                          total_disputes=d["total_disputes"], score=d["score"])

    def _save_rep(self, rep: Reputation) -> None:
        self.reputations[rep.address] = json.dumps({
            "address": rep.address, "jobs_completed": rep.jobs_completed,
            "disputes_won": rep.disputes_won, "disputes_lost": rep.disputes_lost,
            "total_disputes": rep.total_disputes, "score": rep.score,
        }, sort_keys=True)

    def _clamp_score(self, n: int) -> str:
        if n < 0: return "0"
        if n > 100: return "100"
        return str(n)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 1 — create_job
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def create_job(
        self,
        title: str,
        description: str,
        budget: str,
        category: str,
        milestone_count: str,
    ) -> str:
        """
        Post a job with a GEN budget (0.0001 to 10,000,000 GEN).
        Budget is informational — payment handled off-chain between parties.
        AI validators assess feasibility.
        Returns the job ID.
        """
        caller = str(gl.message.sender_address)
        job_id = self._next_job_id()

        # Append GEN to budget if not already there
        budget_display = budget if "GEN" in budget.upper() else budget + " GEN"

        prompt = f"""Evaluate this freelance job.
Title: {title}
Description: {description}
Budget: {budget_display}
Category: {category}

Is it feasible and clearly scoped?
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
            job_id=job_id, client=caller, worker=ZERO_ADDRESS,
            title=title, description=description,
            budget_display=budget_display,
            category=category, status=JOB_OPEN,
            feasibility=feasible_str, feasibility_score=score_str,
            created_at="0", accepted_at="0", submitted_at="0", completed_at="0",
            work_submission="", mediation_suggestion="",
            milestone_count=milestone_count, milestones_completed="0",
            payment_released="false", worker_wallet="",
        )

        self.jobs[job_id] = self._job_to_json(job)
        self.job_ids.append(job_id)

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
        job.accepted_at = "0"
        self.jobs[job_id] = self._job_to_json(job)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 3 — submit_work
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def submit_work(self, job_id: str, submission: str) -> None:
        caller = str(gl.message.sender_address)
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if job.worker != caller:
            raise Exception("Only the assigned worker can submit work")
        if job.status != JOB_ACCEPTED:
            raise Exception("Job must be ACCEPTED")
        job.work_submission = submission
        job.status = JOB_SUBMITTED
        job.submitted_at = "0"
        self.jobs[job_id] = self._job_to_json(job)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 4 — approve_work
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def approve_work(self, job_id: str) -> None:
        """
        Client approves work and marks payment as released.
        Actual GEN transfer happens off-chain to worker_wallet.
        """
        caller = str(gl.message.sender_address)
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if job.client != caller:
            raise Exception("Only the client can approve work")
        if job.status != JOB_SUBMITTED:
            raise Exception("Work has not been submitted yet")
        job.status = JOB_COMPLETED
        job.completed_at = "0"
        job.payment_released = "true"
        self.jobs[job_id] = self._job_to_json(job)

        rep = self._get_rep(job.worker)
        rep.jobs_completed = str(int(rep.jobs_completed) + 1)
        rep.score = self._clamp_score(min(100, int(rep.score) + 5))
        self._save_rep(rep)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 5 — decline_work
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def decline_work(self, job_id: str) -> None:
        """
        Client declines submitted work. Job reopens for a new worker.
        """
        caller = str(gl.message.sender_address)
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if job.client != caller:
            raise Exception("Only the client can decline work")
        if job.status != JOB_SUBMITTED:
            raise Exception("Work has not been submitted yet")
        job.status = JOB_OPEN
        job.worker = ZERO_ADDRESS
        job.worker_wallet = ""
        job.work_submission = ""
        job.submitted_at = "0"
        job.accepted_at = "0"
        self.jobs[job_id] = self._job_to_json(job)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 6 — cancel_job
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def cancel_job(self, job_id: str) -> None:
        """Client cancels an OPEN job."""
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
    #  WRITE 7 — request_mediation
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def request_mediation(self, job_id: str, your_position: str) -> None:
        caller = str(gl.message.sender_address)
        raw = self.jobs.get(job_id, None)
        if raw is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw)
        if caller != job.client and caller != job.worker:
            raise Exception("Only job parties can request mediation")
        if job.status not in [JOB_SUBMITTED, JOB_ACCEPTED]:
            raise Exception("Mediation requires ACCEPTED or SUBMITTED status")

        prompt = f"""Mediate this freelance dispute.
Job: {job.title} | Budget: {job.budget_display}
Work submitted: {job.work_submission if job.work_submission else "None"}
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
    #  WRITE 8 — file_dispute
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def file_dispute(self, job_id: str, your_evidence: str) -> str:
        caller = str(gl.message.sender_address)
        raw_job = self.jobs.get(job_id, None)
        if raw_job is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw_job)
        if caller != job.client and caller != job.worker:
            raise Exception("Only job parties can file a dispute")
        if job.status not in [JOB_SUBMITTED, JOB_ACCEPTED]:
            raise Exception("Cannot dispute this job")

        client_evidence = your_evidence if caller == job.client else ""
        worker_evidence = your_evidence if caller == job.worker else ""

        dispute_id = self._next_dispute_id()

        precedent_raw = self.case_law.get(job.category, "[]")
        precedents = json.loads(precedent_raw)
        precedent_str = ""
        for p in precedents[-3:]:
            if p.get("type") == "dispute":
                precedent_str += f"- {job.category}: {p.get('verdict_pct','?')}% to worker.\n"

        prompt = f"""Judge this freelance dispute. Verdict = % of budget worker deserves.
Job: {job.title} | Budget: {job.budget_display}
Work: {job.work_submission if job.work_submission else "None"}
Client evidence: {client_evidence if client_evidence else "None"}
Worker evidence: {worker_evidence if worker_evidence else "None"}
Prior cases: {precedent_str if precedent_str else "None"}

Valid verdicts: 0, 25, 50, 75, 100 (% to worker).
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

        dispute = Dispute(
            dispute_id=dispute_id, job_id=job_id,
            filer=caller,
            defendant=job.worker if caller == job.client else job.client,
            client_evidence=client_evidence, worker_evidence=worker_evidence,
            verdict_pct=verdict_pct, verdict_reasoning=reasoning,
            appeal_verdict_pct="", appeal_reasoning="",
            status=DISPUTE_RESOLVED, created_at="0", resolved_at="0",
            category=job.category,
        )

        self.disputes[dispute_id] = self._dispute_to_json(dispute)
        self.dispute_ids.append(dispute_id)

        job.status = JOB_RESOLVED
        self.jobs[job_id] = self._job_to_json(job)

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
    #  WRITE 9 — appeal_verdict
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def appeal_verdict(self, dispute_id: str, appeal_grounds: str) -> None:
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

        prompt = f"""Review this freelance dispute appeal. Strict standard — overturn only on clear error or new evidence.
Job: {job.title} | Budget: {job.budget_display}
Original verdict: {dispute.verdict_pct}% to worker | Reasoning: {dispute.verdict_reasoning}
Appeal grounds: {appeal_grounds}
Client evidence: {dispute.client_evidence if dispute.client_evidence else "None"}
Worker evidence: {dispute.worker_evidence if dispute.worker_evidence else "None"}

Valid verdicts: 0, 25, 50, 75, 100.
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

        dispute.appeal_verdict_pct = str(ai.get("appeal_verdict_pct", dispute.verdict_pct))
        dispute.appeal_reasoning = ai.get("reasoning", "")
        dispute.status = DISPUTE_FINAL
        self.disputes[dispute_id] = self._dispute_to_json(dispute)

    # ════════════════════════════════════════════════════════════════
    #  WRITE 10 — verify_milestone
    # ════════════════════════════════════════════════════════════════

    @gl.public.write
    def verify_milestone(self, job_id: str, milestone_description: str, proof_of_completion: str) -> None:
        caller = str(gl.message.sender_address)
        raw_job = self.jobs.get(job_id, None)
        if raw_job is None:
            raise Exception("Job not found")
        job = self._job_from_json(raw_job)
        if job.worker != caller:
            raise Exception("Only the worker can submit milestone proof")
        if job.status not in [JOB_ACCEPTED, JOB_SUBMITTED]:
            raise Exception("Job must be active")

        total = int(job.milestone_count) if job.milestone_count and job.milestone_count != "0" else 1
        completed = int(job.milestones_completed)

        if completed >= total:
            raise Exception("All milestones already completed")

        prompt = f"""Verify this freelance milestone.
Job: {job.title} | Milestone {completed+1} of {total}
Milestone: {milestone_description}
Proof: {proof_of_completion}

Was this milestone genuinely completed?
Respond ONLY with JSON:
{{"milestone_met": true or false, "confidence": <0-100>, "feedback": "<feedback>", "next_steps": "<next steps>"}}"""

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
                return leader_data["milestone_met"] == my_data["milestone_met"]
            except Exception:
                return False

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        ai = json.loads(raw_result)

        if ai.get("milestone_met", False):
            job.milestones_completed = str(completed + 1)
            if completed + 1 >= total and job.status == JOB_ACCEPTED:
                job.status = JOB_SUBMITTED
                job.submitted_at = "0"

        self.jobs[job_id] = self._job_to_json(job)

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
                               "disputes_won": "0", "disputes_lost": "0",
                               "total_disputes": "0", "score": "50"})
        return raw

    @gl.public.view
    def get_case_law(self, category: str) -> str:
        return self.case_law.get(category, "[]")

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
        for jid in self.job_ids:
            raw = self.jobs.get(jid, None)
            if raw is not None:
                d = json.loads(raw)
                if d.get("status") == JOB_OPEN:
                    open_jobs += 1
                elif d.get("status") == JOB_COMPLETED:
                    completed_jobs += 1
        return json.dumps({
            "total_jobs": str(total_jobs),
            "total_disputes": str(total_disputes),
            "open_jobs": str(open_jobs),
            "completed_jobs": str(completed_jobs),
        }, sort_keys=True)
