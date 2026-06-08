# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ArbitrEx v2 — Court of the Internet for Freelance Work                ║
# ║  Built on GenLayer | AI Validators ARE the judges                       ║
# ║  Author: Albert (Manablaq)                                              ║
# ║  v2: proper typed storage, run_nondet_unsafe, response_format='json'    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

from genlayer import *
import json

# ── CONSTANTS ──────────────────────────────────────────────────────────────

CATEGORIES     = ["CODE", "DESIGN", "WRITING", "MEDIA", "OTHER"]
VALID_VERDICTS = [0, 25, 50, 75, 100]

# ── STORAGE TYPES ──────────────────────────────────────────────────────────

@allow_storage
@dataclass
class Reputation:
    completed:  u32
    won:        u32
    lost:       u32
    bad_faith:  u32

@allow_storage
@dataclass
class Escrow:
    amount:    u256
    released:  u256
    refunded:  u256

@allow_storage
@dataclass
class Milestone:
    description:  str
    deliverable:  str
    budget:       u256
    completed:    bool
    quality:      u32
    feedback:     str

@allow_storage
@dataclass
class AiAssessment:
    feasible:  bool
    clarity:   u32
    risk:      str
    issues:    str
    improved:  str

@allow_storage
@dataclass
class Job:
    client:        Address
    freelancer:    Address
    title:         str
    requirements:  str
    category:      str
    budget:        u256
    deadline_days: u32
    status:        str
    work_url:      str
    work_desc:     str
    milestones:    DynArray[Milestone]
    assessment:    AiAssessment

@allow_storage
@dataclass
class Dispute:
    job_id:               str
    filed_by:             Address
    client_evidence:      str
    freelancer_evidence:  str
    verdict_pct:          u32
    reasoning:            str
    key_factor:           str
    confidence:           u32
    precedent_applied:    bool
    freelancer_payment:   u256
    client_refund:        u256
    status:               str
    appeal_count:         u32
    appeal_upheld:        bool
    appeal_reasoning:     str
    final_verdict_pct:    u32

@allow_storage
@dataclass
class CaseLaw:
    dispute_id:  str
    category:    str
    verdict_pct: u32
    confidence:  u32
    summary:     str

# ── PURE HELPERS (no storage access — safe anywhere) ───────────────────────

def _rep_score(rep: Reputation) -> int:
    completed = int(rep.completed)
    won       = int(rep.won)
    lost      = int(rep.lost)
    bad_faith = int(rep.bad_faith)
    if completed == 0:
        return 50
    win_rate          = won / max(1, won + lost)
    completion_bonus  = min(completed * 2, 30)
    bad_faith_penalty = bad_faith * 15
    score = int(50 + (win_rate * 30) + completion_bonus - bad_faith_penalty)
    return max(0, min(100, score))

def _rep_label(score: int) -> str:
    if score >= 90: return "LEGENDARY"
    if score >= 75: return "TRUSTED"
    if score >= 60: return "RELIABLE"
    if score >= 40: return "NEUTRAL"
    if score >= 20: return "CAUTION"
    return "FLAGGED"

def _nearest_verdict(v: int) -> int:
    return min(VALID_VERDICTS, key=lambda x: abs(x - v))

def _category_criteria(category: str) -> str:
    if category == "CODE":
        return (
            "CATEGORY: SOFTWARE DEVELOPMENT\n"
            "Evaluate:\n"
            "- Does the code meet ALL functional requirements stated?\n"
            "- Is the implementation complete (not just partial)?\n"
            "- Are there obvious bugs, security holes, or missing features?\n"
            "- Does the tech stack match what was requested?\n"
            "- Is the code structured and readable?\n"
        )
    elif category == "DESIGN":
        return (
            "CATEGORY: DESIGN WORK\n"
            "Evaluate:\n"
            "- Does the design match the stated style, brand, and aesthetic?\n"
            "- Are all requested deliverables present (formats, sizes, files)?\n"
            "- Does it meet specified platform or dimension requirements?\n"
            "- Is the quality professional and appropriate for the brief?\n"
        )
    elif category == "WRITING":
        return (
            "CATEGORY: WRITTEN CONTENT\n"
            "Evaluate:\n"
            "- Does the writing match the requested topic, tone, and length?\n"
            "- Is the word count within the specified range?\n"
            "- Is the content original and not plagiarized?\n"
            "- Does it follow specified style guidelines (citations, format)?\n"
        )
    elif category == "MEDIA":
        return (
            "CATEGORY: VIDEO / AUDIO / MEDIA\n"
            "Evaluate:\n"
            "- Does the media match the requested format and duration?\n"
            "- Does the content cover the requested topics?\n"
            "- Is the quality appropriate for the brief?\n"
            "- Are all requested elements present?\n"
        )
    return (
        "CATEGORY: GENERAL WORK\n"
        "Evaluate:\n"
        "- Does the work meet all stated requirements?\n"
        "- Is the scope fully covered?\n"
        "- Is the quality appropriate for the brief?\n"
    )

def _safe_parse_json(raw: str, fallback: dict) -> dict:
    """Strip markdown fences and parse JSON safely."""
    try:
        clean = raw.strip().strip('`')
        if clean.lower().startswith('json'):
            clean = clean[4:].strip()
        return json.loads(clean)
    except Exception:
        return fallback


# ══════════════════════════════════════════════════════════════════════════
# CONTRACT
# ══════════════════════════════════════════════════════════════════════════

class ArbitrEx(gl.Contract):

    # ── TYPED STORAGE ─────────────────────────────────────────────────────
    jobs:             TreeMap[str, Job]
    disputes:         TreeMap[str, Dispute]
    reputations:      TreeMap[str, Reputation]
    escrow:           TreeMap[str, Escrow]
    case_law:         DynArray[CaseLaw]
    job_counter:      u32
    dispute_counter:  u32

    def __init__(self):
        self.job_counter     = u32(0)
        self.dispute_counter = u32(0)

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 1: create_job
    # VALIDATOR CALL 1 — Impossible Task Detector.
    # AI validators assess job feasibility BEFORE money locks.
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def create_job(
        self,
        title:          str,
        requirements:   str,
        category:       str,
        budget:         int,
        deadline_days:  int
    ) -> str:
        cat = category.upper()
        if cat not in CATEGORIES:
            return json.dumps({"status": "error", "message": "Category must be: CODE, DESIGN, WRITING, MEDIA, or OTHER"})
        if len(requirements.strip()) < 20:
            return json.dumps({"status": "error", "message": "Requirements must be at least 20 characters."})
        if budget <= 0:
            return json.dumps({"status": "error", "message": "Budget must be > 0."})

        client = gl.message.sender_address

        # ── VALIDATOR CALL 1: Feasibility check ───────────────────────────
        prompt = (
            "You are the GenLayer Impossible Task Detector — an AI system that "
            "evaluates freelance job postings BEFORE money is locked in escrow.\n\n"
            "JOB POSTING:\n"
            "Title: " + title + "\n"
            "Category: " + cat + "\n"
            "Requirements: " + requirements + "\n"
            "Budget: " + str(budget) + " GEN\n"
            "Deadline: " + str(deadline_days) + " days\n\n"
            "Evaluate this posting and respond ONLY with valid JSON:\n"
            "{\"feasible\": true or false, "
            "\"clarity_score\": 0-100, "
            "\"risk_level\": \"LOW\" or \"MEDIUM\" or \"HIGH\", "
            "\"issues\": \"specific problems found or empty string\", "
            "\"improved_requirements\": \"suggested clearer version or empty string\"}\n\n"
            "Rules:\n"
            "- feasible: false only if requirements are CONTRADICTORY or IMPOSSIBLE\n"
            "- clarity_score: 100 = crystal clear, 0 = completely vague\n"
            "- risk_level: likelihood this job results in a dispute\n"
            "- issues: list specific vague or problematic phrases\n"
            "- improved_requirements: only if there are real improvements\n"
            "Respond ONLY with the JSON. No extra text."
        )

        def leader_fn():
            return gl.nondet.exec_prompt(prompt, response_format='json')

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my = gl.nondet.exec_prompt(prompt, response_format='json')
            if not isinstance(my, dict) or not isinstance(leaders_res.calldata, dict):
                return False
            # Equivalent if: feasible matches AND clarity within 20 AND risk matches
            feasible_match = my.get("feasible") == leaders_res.calldata.get("feasible")
            clarity_match  = abs(int(my.get("clarity_score", 50)) - int(leaders_res.calldata.get("clarity_score", 50))) <= 20
            risk_match     = my.get("risk_level") == leaders_res.calldata.get("risk_level")
            return feasible_match and clarity_match and risk_match

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        fd = _safe_parse_json(raw if isinstance(raw, str) else json.dumps(raw), {
            "feasible": True, "clarity_score": 50,
            "risk_level": "MEDIUM", "issues": "", "improved_requirements": ""
        })
        if isinstance(raw, dict):
            fd = raw

        feasible = bool(fd.get("feasible", True))
        clarity  = int(fd.get("clarity_score", 50))
        risk     = str(fd.get("risk_level", "MEDIUM"))
        issues   = str(fd.get("issues", ""))
        improved = str(fd.get("improved_requirements", ""))

        # Store job
        self.job_counter += u32(1)
        job_id = "job_" + str(int(self.job_counter))

        assessment = AiAssessment(
            feasible=feasible,
            clarity=u32(clarity),
            risk=risk,
            issues=issues,
            improved=improved
        )

        self.jobs[job_id] = Job(
            client=client,
            freelancer=Address.ZERO,
            title=title,
            requirements=requirements,
            category=cat,
            budget=u256(budget),
            deadline_days=u32(deadline_days),
            status="OPEN",
            work_url="",
            work_desc="",
            milestones=DynArray[Milestone](),
            assessment=assessment
        )

        self.escrow[job_id] = Escrow(
            amount=u256(budget),
            released=u256(0),
            refunded=u256(0)
        )

        return json.dumps({
            "status":   "created",
            "job_id":   job_id,
            "feasible": feasible,
            "clarity":  clarity,
            "risk":     risk,
            "issues":   issues,
            "improved": improved,
            "message":  "Job created and assessed by GenLayer AI validators."
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 2: accept_job
    # Freelancer claims the job and locks in.
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def accept_job(self, job_id: str) -> str:
        if job_id not in self.jobs:
            return json.dumps({"status": "error", "message": "Job not found."})
        job = self.jobs[job_id]
        if job.status != "OPEN":
            return json.dumps({"status": "error", "message": "Job is not open."})

        freelancer = gl.message.sender_address
        if job.client == freelancer:
            return json.dumps({"status": "error", "message": "Client cannot accept their own job."})

        self.jobs[job_id].freelancer = freelancer
        self.jobs[job_id].status     = "IN_PROGRESS"
        self._init_rep(str(freelancer))

        return json.dumps({
            "status":  "accepted",
            "job_id":  job_id,
            "message": "Job accepted. Submit work when ready via submit_work."
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 3: submit_work
    # Freelancer submits completed work for client review.
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def submit_work(
        self,
        job_id:           str,
        work_url:         str,
        work_description: str
    ) -> str:
        if job_id not in self.jobs:
            return json.dumps({"status": "error", "message": "Job not found."})
        job = self.jobs[job_id]
        freelancer = gl.message.sender_address
        if job.freelancer != freelancer:
            return json.dumps({"status": "error", "message": "Only the assigned freelancer can submit."})
        if job.status != "IN_PROGRESS":
            return json.dumps({"status": "error", "message": "Job is not in progress."})

        self.jobs[job_id].work_url  = work_url
        self.jobs[job_id].work_desc = work_description
        self.jobs[job_id].status    = "UNDER_REVIEW"

        return json.dumps({
            "status":  "submitted",
            "job_id":  job_id,
            "message": "Work submitted. Client can approve or open a dispute."
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 4: approve_work
    # Client approves work — releases full escrow to freelancer.
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def approve_work(self, job_id: str) -> str:
        if job_id not in self.jobs:
            return json.dumps({"status": "error", "message": "Job not found."})
        job = self.jobs[job_id]
        client = gl.message.sender_address
        if job.client != client:
            return json.dumps({"status": "error", "message": "Only the client can approve."})
        if job.status != "UNDER_REVIEW":
            return json.dumps({"status": "error", "message": "No work submitted for review."})

        amt = int(self.escrow[job_id].amount)
        self.jobs[job_id].status         = "COMPLETED"
        self.escrow[job_id].released      = u256(amt)
        self._inc_rep(str(job.freelancer), "completed")
        self._init_rep(str(client))

        return json.dumps({
            "status":  "completed",
            "job_id":  job_id,
            "paid":    amt,
            "message": "Work approved. " + str(amt) + " GEN released to freelancer."
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 5: request_mediation
    # VALIDATOR CALL 2 — AI mediators suggest compromise before formal dispute.
    # Saves time. Resolves conflicts faster. No formal dispute needed.
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def request_mediation(self, job_id: str, issue: str) -> str:
        if job_id not in self.jobs:
            return json.dumps({"status": "error", "message": "Job not found."})
        job       = self.jobs[job_id]
        requester = gl.message.sender_address
        if requester not in [job.client, job.freelancer]:
            return json.dumps({"status": "error", "message": "Only job parties can request mediation."})
        if job.status not in ["UNDER_REVIEW", "IN_PROGRESS"]:
            return json.dumps({"status": "error", "message": "Job is not in a mediatable state."})

        work_status = (
            "Work submitted: " + job.work_desc + " | URL: " + job.work_url
            if job.work_url else "Work not yet submitted."
        )
        requester_role = "CLIENT" if requester == job.client else "FREELANCER"

        # Copy to memory for nondet block
        job_mem = gl.storage.copy_to_memory(job)

        prompt = (
            "You are an AI Mediator on the GenLayer Court of the Internet.\n"
            "Your goal: suggest a FAIR COMPROMISE before a formal dispute is filed.\n\n"
            "JOB DETAILS:\n"
            "Title: " + job_mem.title + "\n"
            "Category: " + job_mem.category + "\n"
            "Requirements: " + job_mem.requirements + "\n"
            "Budget: " + str(int(job_mem.budget)) + " GEN\n"
            "Work status: " + work_status + "\n\n"
            "ISSUE RAISED BY " + requester_role + ":\n"
            + issue + "\n\n"
            "Suggest a specific, fair compromise. Respond ONLY with valid JSON:\n"
            "{\"compromise_summary\": \"1-2 sentence compromise\", "
            "\"client_should\": \"specific action for client\", "
            "\"freelancer_should\": \"specific action for freelancer\", "
            "\"suggested_payment_pct\": 0-100, "
            "\"rationale\": \"why this split is fair\"}\n\n"
            "Be concrete. Name specific actions. No extra text."
        )

        def leader_fn():
            return gl.nondet.exec_prompt(prompt, response_format='json')

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my = gl.nondet.exec_prompt(prompt, response_format='json')
            if not isinstance(my, dict) or not isinstance(leaders_res.calldata, dict):
                return False
            # Equivalent if payment_pct within 15 AND both lean same direction
            my_pct     = int(my.get("suggested_payment_pct", 50))
            lead_pct   = int(leaders_res.calldata.get("suggested_payment_pct", 50))
            pct_match  = abs(my_pct - lead_pct) <= 15
            same_lean  = (my_pct >= 50) == (lead_pct >= 50)
            return pct_match and same_lean

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        md = raw if isinstance(raw, dict) else _safe_parse_json(
            raw if isinstance(raw, str) else "",
            {
                "compromise_summary": "Equal split recommended.",
                "client_should": "Review the work carefully.",
                "freelancer_should": "Address the raised concerns.",
                "suggested_payment_pct": 50,
                "rationale": "Equal split given ambiguity."
            }
        )

        return json.dumps({
            "status":                "mediation_complete",
            "job_id":                job_id,
            "compromise":            md.get("compromise_summary", ""),
            "client_should":         md.get("client_should", ""),
            "freelancer_should":     md.get("freelancer_should", ""),
            "suggested_payment_pct": md.get("suggested_payment_pct", 50),
            "rationale":             md.get("rationale", ""),
            "message": (
                "GenLayer AI mediators have reached consensus on a compromise. "
                "Accept it or proceed to formal dispute via file_dispute."
            )
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 6: file_dispute  ← CORE AI MECHANIC
    # VALIDATOR CALL 3 — 5 validators independently judge the dispute.
    # Graduated verdict: 0/25/50/75/100% to freelancer.
    # On-chain reasoning. Precedent stored permanently.
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def file_dispute(
        self,
        job_id:              str,
        client_evidence:     str,
        freelancer_evidence: str
    ) -> str:
        if job_id not in self.jobs:
            return json.dumps({"status": "error", "message": "Job not found."})
        job      = self.jobs[job_id]
        filed_by = gl.message.sender_address
        if filed_by not in [job.client, job.freelancer]:
            return json.dumps({"status": "error", "message": "Only job parties can file a dispute."})
        if job.status not in ["UNDER_REVIEW", "IN_PROGRESS"]:
            return json.dumps({"status": "error", "message": "Job is not in a disputable state."})

        # Build reputation context
        client_score = 50
        fl_score     = 50
        client_key   = str(job.client)
        fl_key       = str(job.freelancer)
        if client_key in self.reputations:
            client_score = _rep_score(self.reputations[client_key])
        if fl_key in self.reputations:
            fl_score = _rep_score(self.reputations[fl_key])

        # Build precedent context (last 3 from same category)
        prec_text = ""
        same_cat  = [c for c in self.case_law if c.category == job.category]
        recent    = same_cat[-3:] if len(same_cat) >= 3 else same_cat
        if recent:
            prec_text = "\nPRECEDENTS (similar past cases on this platform):\n"
            for p in recent:
                prec_text += (
                    "- Case " + p.dispute_id + ": "
                    + p.summary + " -> "
                    + str(int(p.verdict_pct)) + "% to freelancer\n"
                )

        criteria = _category_criteria(job.category)

        # Copy to memory for nondet block
        job_mem = gl.storage.copy_to_memory(job)

        prompt = (
            "=======================================================\n"
            "  GENLAYER COURT OF THE INTERNET - CASE FILE\n"
            "=======================================================\n"
            "You are a judge in a decentralized AI arbitration system.\n"
            "5 independent validators will each rule on this case.\n"
            "Optimistic Democracy consensus determines the final verdict.\n\n"
            "-- JOB DETAILS --\n"
            "Title:    " + job_mem.title + "\n"
            "Category: " + job_mem.category + "\n"
            "Budget:   " + str(int(job_mem.budget)) + " GEN\n\n"
            "-- CLIENT'S REQUIREMENTS --\n"
            + job_mem.requirements + "\n\n"
            "-- FREELANCER'S SUBMITTED WORK --\n"
            "URL:         " + (job_mem.work_url or "Not provided") + "\n"
            "Description: " + (job_mem.work_desc or "Not provided") + "\n\n"
            "-- CLIENT'S EVIDENCE / CLAIM --\n"
            + client_evidence + "\n\n"
            "-- FREELANCER'S EVIDENCE / DEFENSE --\n"
            + freelancer_evidence + "\n\n"
            "-- REPUTATION CONTEXT --\n"
            "Client reputation:     " + str(client_score) + "/100 (" + _rep_label(client_score) + ")\n"
            "Freelancer reputation: " + str(fl_score) + "/100 (" + _rep_label(fl_score) + ")\n"
            + prec_text + "\n"
            "-- EVALUATION CRITERIA --\n"
            + criteria + "\n"
            "-- YOUR VERDICT --\n"
            "Issue a GRADUATED VERDICT. Respond ONLY with valid JSON:\n"
            "{\"verdict_pct\": 0 or 25 or 50 or 75 or 100, "
            "\"reasoning\": \"2-3 sentences explaining your ruling\", "
            "\"key_factor\": \"the single most decisive factor\", "
            "\"confidence\": 0-100, "
            "\"precedent_applied\": true or false}\n\n"
            "Verdict guide:\n"
            "0   = Freelancer failed completely or committed fraud\n"
            "25  = Mostly failed, minor partial credit warranted\n"
            "50  = Genuinely disputed, both parties have valid points\n"
            "75  = Mostly completed with minor shortfalls\n"
            "100 = Fully completed, client is being unreasonable\n\n"
            "Base verdict ONLY on evidence. Be fair, specific, objective.\n"
            "No extra text beyond the JSON."
        )

        def leader_fn():
            return gl.nondet.exec_prompt(prompt, response_format='json')

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my = gl.nondet.exec_prompt(prompt, response_format='json')
            if not isinstance(my, dict) or not isinstance(leaders_res.calldata, dict):
                return False
            my_pct   = _nearest_verdict(int(my.get("verdict_pct", 50)))
            lead_pct = _nearest_verdict(int(leaders_res.calldata.get("verdict_pct", 50)))
            # Equivalent if within 25 points AND favor same party
            return (
                abs(my_pct - lead_pct) <= 25 and
                (my_pct >= 50) == (lead_pct >= 50)
            )

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        vd = raw if isinstance(raw, dict) else _safe_parse_json(
            raw if isinstance(raw, str) else "",
            {"verdict_pct": 50, "reasoning": "", "key_factor": "", "confidence": 60, "precedent_applied": False}
        )

        verdict_pct   = _nearest_verdict(int(vd.get("verdict_pct", 50)))
        reasoning     = str(vd.get("reasoning", ""))
        key_factor    = str(vd.get("key_factor", ""))
        confidence    = int(vd.get("confidence", 75))
        prec_applied  = bool(vd.get("precedent_applied", False))

        total               = int(job.budget)
        freelancer_payment  = int(total * verdict_pct / 100)
        client_refund       = total - freelancer_payment

        # Generate dispute ID
        self.dispute_counter += u32(1)
        dispute_id = "dispute_" + str(int(self.dispute_counter))

        # Store dispute with full on-chain reasoning
        self.disputes[dispute_id] = Dispute(
            job_id=job_id,
            filed_by=filed_by,
            client_evidence=client_evidence,
            freelancer_evidence=freelancer_evidence,
            verdict_pct=u32(verdict_pct),
            reasoning=reasoning,
            key_factor=key_factor,
            confidence=u32(confidence),
            precedent_applied=prec_applied,
            freelancer_payment=u256(freelancer_payment),
            client_refund=u256(client_refund),
            status="RESOLVED",
            appeal_count=u32(0),
            appeal_upheld=False,
            appeal_reasoning="",
            final_verdict_pct=u32(verdict_pct)
        )

        # Update job and escrow
        self.jobs[job_id].status          = "DISPUTE_RESOLVED"
        self.escrow[job_id].released       = u256(freelancer_payment)
        self.escrow[job_id].refunded       = u256(client_refund)

        # Update reputations
        fl_str = str(job.freelancer)
        cl_str = str(job.client)
        if verdict_pct >= 50:
            self._inc_rep(fl_str, "won")
            self._inc_rep(cl_str, "lost")
        else:
            self._inc_rep(cl_str, "won")
            self._inc_rep(fl_str, "lost")

        # Store precedent (keep last 25)
        summary = job.title[:60] + " | Key: " + key_factor[:80]
        self.case_law.append(CaseLaw(
            dispute_id=dispute_id,
            category=job.category,
            verdict_pct=u32(verdict_pct),
            confidence=u32(confidence),
            summary=summary
        ))
        while len(self.case_law) > 25:
            self.case_law.pop(0)

        return json.dumps({
            "status":             "verdict_issued",
            "dispute_id":         dispute_id,
            "verdict_pct":        verdict_pct,
            "reasoning":          reasoning,
            "key_factor":         key_factor,
            "confidence":         confidence,
            "precedent_applied":  prec_applied,
            "freelancer_payment": freelancer_payment,
            "client_refund":      client_refund,
            "validators":         5,
            "consensus_method":   "Optimistic Democracy",
            "message": "5 GenLayer validators reached consensus. Verdict is final unless appealed."
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 7: appeal_verdict
    # VALIDATOR CALL 4 — Court of Appeals with STRICTER standard.
    # Only overturns if original verdict was clearly wrong.
    # One appeal only. This verdict is permanent.
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def appeal_verdict(self, dispute_id: str, appeal_reason: str) -> str:
        if dispute_id not in self.disputes:
            return json.dumps({"status": "error", "message": "Dispute not found."})
        dispute   = self.disputes[dispute_id]
        appellant = gl.message.sender_address
        if dispute.status != "RESOLVED":
            return json.dumps({"status": "error", "message": "Dispute is not appealable."})
        if int(dispute.appeal_count) >= 1:
            return json.dumps({"status": "error", "message": "Maximum one appeal. This verdict is final."})

        job_id = dispute.job_id
        job    = self.jobs[job_id] if job_id in self.jobs else None

        # Copy to memory for nondet block
        dispute_mem = gl.storage.copy_to_memory(dispute)
        job_title   = job.title if job else ""
        job_cat     = job.category if job else ""
        job_req     = job.requirements if job else ""

        prompt = (
            "=======================================================\n"
            "  GENLAYER COURT OF APPEALS - APPELLATE REVIEW\n"
            "=======================================================\n"
            "You are a SENIOR APPELLATE JUDGE reviewing a lower court ruling.\n"
            "Your standard is STRICTER: only overturn if the original verdict\n"
            "was CLEARLY and DEMONSTRABLY wrong based on the evidence.\n\n"
            "-- ORIGINAL CASE --\n"
            "Job:          " + job_title + "\n"
            "Category:     " + job_cat + "\n"
            "Requirements: " + job_req + "\n\n"
            "-- ORIGINAL EVIDENCE --\n"
            "Client:     " + dispute_mem.client_evidence + "\n"
            "Freelancer: " + dispute_mem.freelancer_evidence + "\n\n"
            "-- ORIGINAL VERDICT --\n"
            "Verdict: " + str(int(dispute_mem.verdict_pct)) + "% to freelancer\n"
            "Reasoning: " + dispute_mem.reasoning + "\n"
            "Key factor: " + dispute_mem.key_factor + "\n\n"
            "-- APPEAL ARGUMENT --\n"
            + appeal_reason + "\n\n"
            "-- YOUR APPELLATE RULING --\n"
            "Respond ONLY with valid JSON:\n"
            "{\"upheld\": true or false, "
            "\"new_verdict_pct\": 0 or 25 or 50 or 75 or 100, "
            "\"appellate_reasoning\": \"2-3 sentences on why you upheld or overturned\", "
            "\"confidence\": 0-100}\n\n"
            "upheld=true means the original verdict stands.\n"
            "upheld=false means you are overturning it.\n"
            "Apply the HIGHEST evidentiary standard. No extra text."
        )

        def leader_fn():
            return gl.nondet.exec_prompt(prompt, response_format='json')

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my = gl.nondet.exec_prompt(prompt, response_format='json')
            if not isinstance(my, dict) or not isinstance(leaders_res.calldata, dict):
                return False
            # Court of Appeals: both must agree on upheld/overturned
            # AND if overturning, new verdicts within 25 points
            my_upheld   = bool(my.get("upheld", True))
            lead_upheld = bool(leaders_res.calldata.get("upheld", True))
            if my_upheld != lead_upheld:
                return False
            if not my_upheld:
                my_pct   = _nearest_verdict(int(my.get("new_verdict_pct", 50)))
                lead_pct = _nearest_verdict(int(leaders_res.calldata.get("new_verdict_pct", 50)))
                return abs(my_pct - lead_pct) <= 25
            return True

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        ad = raw if isinstance(raw, dict) else _safe_parse_json(
            raw if isinstance(raw, str) else "",
            {"upheld": True, "new_verdict_pct": int(dispute.verdict_pct), "appellate_reasoning": "", "confidence": 85}
        )

        upheld     = bool(ad.get("upheld", True))
        new_pct    = _nearest_verdict(int(ad.get("new_verdict_pct", int(dispute.verdict_pct))))
        reasoning  = str(ad.get("appellate_reasoning", ""))
        confidence = int(ad.get("confidence", 85))
        final_pct  = int(dispute.verdict_pct) if upheld else new_pct

        self.disputes[dispute_id].appeal_count      = u32(1)
        self.disputes[dispute_id].appeal_upheld      = upheld
        self.disputes[dispute_id].appeal_reasoning   = reasoning
        self.disputes[dispute_id].final_verdict_pct  = u32(final_pct)
        self.disputes[dispute_id].status             = "APPEAL_FINAL"

        if not upheld and job:
            total          = int(job.budget)
            new_fl_payment = int(total * final_pct / 100)
            new_cl_refund  = total - new_fl_payment
            self.disputes[dispute_id].freelancer_payment = u256(new_fl_payment)
            self.disputes[dispute_id].client_refund      = u256(new_cl_refund)
            if job_id in self.escrow:
                self.escrow[job_id].released = u256(new_fl_payment)
                self.escrow[job_id].refunded = u256(new_cl_refund)

        return json.dumps({
            "status":            "appeal_final",
            "dispute_id":        dispute_id,
            "upheld":            upheld,
            "final_verdict_pct": final_pct,
            "appellate_reasoning": reasoning,
            "confidence":        confidence,
            "freelancer_payment": int(self.disputes[dispute_id].freelancer_payment),
            "client_refund":     int(self.disputes[dispute_id].client_refund),
            "message": "Court of Appeals has ruled. No further appeals. This verdict is permanent."
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 8: verify_milestone
    # VALIDATOR CALL 5 — Validators verify milestone completion.
    # Staged payment releases without needing a full dispute.
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def verify_milestone(
        self,
        job_id:                 str,
        milestone_desc:         str,
        freelancer_deliverable: str,
        milestone_budget:       int
    ) -> str:
        if job_id not in self.jobs:
            return json.dumps({"status": "error", "message": "Job not found."})
        job    = self.jobs[job_id]
        client = gl.message.sender_address
        if job.client != client:
            return json.dumps({"status": "error", "message": "Only the client can verify milestones."})
        if job.status not in ["IN_PROGRESS", "UNDER_REVIEW"]:
            return json.dumps({"status": "error", "message": "Job is not active."})

        # Copy to memory for nondet block
        job_mem = gl.storage.copy_to_memory(job)
        criteria = _category_criteria(job_mem.category)

        prompt = (
            "You are a milestone evaluator on the GenLayer Court of the Internet.\n"
            "Evaluate whether a freelancer's deliverable meets the milestone requirements.\n\n"
            "FULL JOB CONTEXT:\n"
            "Title:    " + job_mem.title + "\n"
            "Category: " + job_mem.category + "\n"
            "Overall requirements: " + job_mem.requirements + "\n\n"
            "THIS MILESTONE:\n"
            "Description:  " + milestone_desc + "\n"
            "Budget:       " + str(milestone_budget) + " GEN\n\n"
            "FREELANCER'S DELIVERABLE:\n"
            + freelancer_deliverable + "\n\n"
            + criteria + "\n"
            "Respond ONLY with valid JSON:\n"
            "{\"completed\": true or false, "
            "\"quality_score\": 0-100, "
            "\"passed_criteria\": [\"criterion 1\", \"criterion 2\"], "
            "\"failed_criteria\": [\"criterion 1\", \"criterion 2\"], "
            "\"feedback\": \"specific actionable feedback\"}\n\n"
            "No extra text."
        )

        def leader_fn():
            return gl.nondet.exec_prompt(prompt, response_format='json')

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my = gl.nondet.exec_prompt(prompt, response_format='json')
            if not isinstance(my, dict) or not isinstance(leaders_res.calldata, dict):
                return False
            # Equivalent if: completed matches AND quality within 20
            completed_match = my.get("completed") == leaders_res.calldata.get("completed")
            quality_match   = abs(int(my.get("quality_score", 50)) - int(leaders_res.calldata.get("quality_score", 50))) <= 20
            return completed_match and quality_match

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        mv = raw if isinstance(raw, dict) else _safe_parse_json(
            raw if isinstance(raw, str) else "",
            {"completed": False, "quality_score": 50, "passed_criteria": [], "failed_criteria": [], "feedback": ""}
        )

        completed = bool(mv.get("completed", False))
        quality   = int(mv.get("quality_score", 50))
        passed    = mv.get("passed_criteria", [])
        failed    = mv.get("failed_criteria", [])
        feedback  = str(mv.get("feedback", ""))

        self.jobs[job_id].milestones.append(Milestone(
            description=milestone_desc,
            deliverable=freelancer_deliverable,
            budget=u256(milestone_budget),
            completed=completed,
            quality=u32(quality),
            feedback=feedback
        ))

        return json.dumps({
            "status":           "milestone_verified",
            "completed":        completed,
            "quality_score":    quality,
            "passed_criteria":  passed,
            "failed_criteria":  failed,
            "feedback":         feedback,
            "payment_released": milestone_budget if completed else 0,
            "message": (
                "Milestone approved by GenLayer validators. "
                + str(milestone_budget) + " GEN released."
            ) if completed else (
                "Milestone not completed. " + feedback
            )
        })

    # ══════════════════════════════════════════════════════════════════════
    # READ METHODS
    # ══════════════════════════════════════════════════════════════════════

    @gl.public.view
    def get_job(self, job_id: str) -> str:
        if job_id not in self.jobs:
            return json.dumps({"error": "Job not found."})
        job = self.jobs[job_id]
        milestones = []
        for m in job.milestones:
            milestones.append({
                "description": m.description,
                "budget":      int(m.budget),
                "completed":   m.completed,
                "quality":     int(m.quality),
                "feedback":    m.feedback
            })
        return json.dumps({
            "client":        str(job.client),
            "freelancer":    str(job.freelancer),
            "title":         job.title,
            "requirements":  job.requirements,
            "category":      job.category,
            "budget":        int(job.budget),
            "deadline_days": int(job.deadline_days),
            "status":        job.status,
            "work_url":      job.work_url,
            "work_desc":     job.work_desc,
            "milestones":    milestones,
            "assessment": {
                "feasible": job.assessment.feasible,
                "clarity":  int(job.assessment.clarity),
                "risk":     job.assessment.risk,
                "issues":   job.assessment.issues,
                "improved": job.assessment.improved
            }
        })

    @gl.public.view
    def get_dispute(self, dispute_id: str) -> str:
        if dispute_id not in self.disputes:
            return json.dumps({"error": "Dispute not found."})
        d = self.disputes[dispute_id]
        return json.dumps({
            "job_id":              d.job_id,
            "filed_by":            str(d.filed_by),
            "verdict_pct":         int(d.verdict_pct),
            "reasoning":           d.reasoning,
            "key_factor":          d.key_factor,
            "confidence":          int(d.confidence),
            "precedent_applied":   d.precedent_applied,
            "freelancer_payment":  int(d.freelancer_payment),
            "client_refund":       int(d.client_refund),
            "status":              d.status,
            "appeal_count":        int(d.appeal_count),
            "appeal_upheld":       d.appeal_upheld,
            "appeal_reasoning":    d.appeal_reasoning,
            "final_verdict_pct":   int(d.final_verdict_pct)
        })

    @gl.public.view
    def get_reputation(self, address: str) -> str:
        if address not in self.reputations:
            return json.dumps({
                "address": address, "score": 50, "label": "NEUTRAL",
                "completed": 0, "won": 0, "lost": 0, "bad_faith": 0
            })
        rep   = self.reputations[address]
        score = _rep_score(rep)
        return json.dumps({
            "address":   address,
            "score":     score,
            "label":     _rep_label(score),
            "completed": int(rep.completed),
            "won":       int(rep.won),
            "lost":      int(rep.lost),
            "bad_faith": int(rep.bad_faith)
        })

    @gl.public.view
    def get_case_law(self, category: str) -> str:
        result = []
        for c in self.case_law:
            if category.upper() == "ALL" or c.category == category.upper():
                result.append({
                    "dispute_id":  c.dispute_id,
                    "category":    c.category,
                    "verdict_pct": int(c.verdict_pct),
                    "confidence":  int(c.confidence),
                    "summary":     c.summary
                })
        return json.dumps(result)

    @gl.public.view
    def get_all_jobs(self) -> str:
        result = {}
        for job_id, job in self.jobs.items():
            result[job_id] = {
                "client":   str(job.client),
                "title":    job.title,
                "category": job.category,
                "budget":   int(job.budget),
                "status":   job.status
            }
        return json.dumps(result)

    @gl.public.view
    def get_all_disputes(self) -> str:
        result = {}
        for dispute_id, d in self.disputes.items():
            result[dispute_id] = {
                "job_id":      d.job_id,
                "verdict_pct": int(d.verdict_pct),
                "status":      d.status
            }
        return json.dumps(result)

    @gl.public.view
    def get_platform_stats(self) -> str:
        total_jobs      = len(self.jobs)
        completed_jobs  = 0
        total_volume    = 0
        total_disputes  = len(self.disputes)
        resolved        = 0

        for job in self.jobs.values():
            if job.status == "COMPLETED":
                completed_jobs += 1
            total_volume += int(job.budget)

        for d in self.disputes.values():
            if "RESOLVED" in d.status or "FINAL" in d.status:
                resolved += 1

        return json.dumps({
            "total_jobs":        total_jobs,
            "completed_jobs":    completed_jobs,
            "total_disputes":    total_disputes,
            "resolved_disputes": resolved,
            "total_volume_gen":  total_volume,
            "case_law_entries":  len(self.case_law)
        })

    # ══════════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════════

    def _init_rep(self, address: str):
        if address not in self.reputations:
            self.reputations[address] = Reputation(
                completed=u32(0),
                won=u32(0),
                lost=u32(0),
                bad_faith=u32(0)
            )

    def _inc_rep(self, address: str, field: str):
        self._init_rep(address)
        rep = self.reputations[address]
        if field == "completed":
            self.reputations[address].completed = u32(int(rep.completed) + 1)
        elif field == "won":
            self.reputations[address].won = u32(int(rep.won) + 1)
        elif field == "lost":
            self.reputations[address].lost = u32(int(rep.lost) + 1)
        elif field == "bad_faith":
            self.reputations[address].bad_faith = u32(int(rep.bad_faith) + 1)
