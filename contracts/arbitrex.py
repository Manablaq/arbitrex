# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  ArbitrEx — Court of the Internet for Freelance Work                   ║
# ║  Built on GenLayer | AI Validators ARE the judges                       ║
# ║  Author: Albert (Manablaq)                                              ║
# ║  v4: prompt_comparative pattern — production-ready for Bradbury         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

from genlayer import *
import json

# ── CONSTANTS ──────────────────────────────────────────────────────────────

CATEGORIES     = ["CODE", "DESIGN", "WRITING", "MEDIA", "OTHER"]
VALID_VERDICTS = [0, 25, 50, 75, 100]

# ── HELPERS ────────────────────────────────────────────────────────────────

def _nearest_verdict(v: int) -> int:
    return min(VALID_VERDICTS, key=lambda x: abs(x - v))

def _rep_score(completed: int, won: int, lost: int, bad_faith: int) -> int:
    if completed == 0:
        return 50
    win_rate          = won / max(1, won + lost)
    completion_bonus  = min(completed * 2, 30)
    bad_faith_penalty = bad_faith * 15
    return max(0, min(100, int(50 + (win_rate * 30) + completion_bonus - bad_faith_penalty)))

def _rep_label(score: int) -> str:
    if score >= 90: return "LEGENDARY"
    if score >= 75: return "TRUSTED"
    if score >= 60: return "RELIABLE"
    if score >= 40: return "NEUTRAL"
    if score >= 20: return "CAUTION"
    return "FLAGGED"

def _category_criteria(category: str) -> str:
    if category == "CODE":
        return (
            "CATEGORY: CODE\n"
            "- Does the code meet ALL stated functional requirements?\n"
            "- Is the implementation complete, not partial?\n"
            "- Does the tech stack match what was requested?\n"
        )
    elif category == "DESIGN":
        return (
            "CATEGORY: DESIGN\n"
            "- Does the design match the stated style and brand?\n"
            "- Are all requested deliverables present?\n"
            "- Is the quality professional and appropriate?\n"
        )
    elif category == "WRITING":
        return (
            "CATEGORY: WRITING\n"
            "- Does the writing match the requested topic, tone, and length?\n"
            "- Is the content original?\n"
            "- Does it follow specified style guidelines?\n"
        )
    elif category == "MEDIA":
        return (
            "CATEGORY: MEDIA\n"
            "- Does the media match the requested format and duration?\n"
            "- Does the content cover the requested topics?\n"
            "- Are all requested elements present?\n"
        )
    return (
        "CATEGORY: GENERAL\n"
        "- Does the work meet all stated requirements?\n"
        "- Is the scope fully covered?\n"
        "- Is the quality appropriate?\n"
    )


# ══════════════════════════════════════════════════════════════════════════
# CONTRACT
# ══════════════════════════════════════════════════════════════════════════

class ArbitrEx(gl.Contract):

    # ── STORAGE: TreeMap for lookups, str for counters ───────────────────
    jobs:             TreeMap[str, str]
    disputes:         TreeMap[str, str]
    reputations:      TreeMap[str, str]
    escrow:           TreeMap[str, str]
    case_law:         str
    job_counter:      str
    dispute_counter:  str

    def __init__(self):
        self.jobs            = "{}"
        self.disputes        = "{}"
        self.reputations     = "{}"
        self.escrow          = "{}"
        self.case_law        = "[]"
        self.job_counter     = "0"
        self.dispute_counter = "0"

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 1: create_job
    # VALIDATOR CALL 1 — Impossible Task Detector
    # Pattern: prompt_comparative
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def create_job(
        self,
        title:         str,
        requirements:  str,
        category:      str,
        budget:        int,
        deadline_days: int
    ) -> str:
        cat = category.upper()
        if cat not in CATEGORIES:
            return json.dumps({"status": "error", "message": "Category must be: CODE, DESIGN, WRITING, MEDIA, or OTHER"})
        if len(requirements.strip()) < 20:
            return json.dumps({"status": "error", "message": "Requirements must be at least 20 characters."})
        if budget <= 0:
            return json.dumps({"status": "error", "message": "Budget must be > 0."})

        client = str(gl.message.sender_address)

        # VALIDATOR CALL 1: prompt_comparative — Bradbury production pattern
        def assess_job():
            prompt = (
                "You are the GenLayer Impossible Task Detector.\n"
                "Evaluate this freelance job posting.\n\n"
                "Title: " + title + "\n"
                "Category: " + cat + "\n"
                "Requirements: " + requirements + "\n"
                "Budget: " + str(budget) + " GEN\n"
                "Deadline: " + str(deadline_days) + " days\n\n"
                "Respond ONLY with valid JSON:\n"
                "{\"feasible\": true or false, "
                "\"clarity_score\": 0-100, "
                "\"risk_level\": \"LOW\" or \"MEDIUM\" or \"HIGH\", "
                "\"issues\": \"specific problems or empty string\"}\n\n"
                "feasible=false only if requirements are CONTRADICTORY or IMPOSSIBLE.\n"
                "No extra text."
            )
            result = gl.nondet.exec_prompt(prompt, response_format='json')
            return json.dumps(result, sort_keys=True)

        raw = gl.eq_principle.prompt_comparative(
            assess_job,
            "feasible field must match; clarity_score within 20 points; risk_level must match"
        )

        try:
            fd = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(fd, dict):
                fd = {}
        except Exception:
            fd = {}

        feasible = bool(fd.get("feasible", True))
        clarity  = int(fd.get("clarity_score", 50))
        risk     = str(fd.get("risk_level", "MEDIUM"))
        issues   = str(fd.get("issues", ""))

        self.job_counter = str(int(self.job_counter) + 1)
        job_id = "job_" + str(int(self.job_counter))

        self.jobs[job_id] = json.dumps({
            "client":        client,
            "freelancer":    "",
            "title":         title,
            "requirements":  requirements,
            "category":      cat,
            "budget":        budget,
            "deadline_days": deadline_days,
            "status":        "OPEN",
            "work_url":      "",
            "work_desc":     "",
            "milestones":    [],
            "assessment": {
                "feasible": feasible,
                "clarity":  clarity,
                "risk":     risk,
                "issues":   issues,
                "improved": ""
            }
        })

        self.escrow[job_id] = json.dumps({
            "amount":   budget,
            "released": 0,
            "refunded": 0
        })

        return json.dumps({
            "status":   "created",
            "job_id":   job_id,
            "feasible": feasible,
            "clarity":  clarity,
            "risk":     risk,
            "issues":   issues,
            "message":  "Job assessed by GenLayer AI validators."
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 2: accept_job
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def accept_job(self, job_id: str) -> str:
        if job_id not in self.jobs:
            return json.dumps({"status": "error", "message": "Job not found."})
        job        = json.loads(self.jobs[job_id])
        freelancer = str(gl.message.sender_address)
        if job["status"] != "OPEN":
            return json.dumps({"status": "error", "message": "Job is not open."})
        if job["client"] == freelancer:
            return json.dumps({"status": "error", "message": "Client cannot accept their own job."})
        job["freelancer"] = freelancer
        job["status"]     = "IN_PROGRESS"
        self.jobs[job_id] = json.dumps(job)
        self._init_rep(freelancer)
        return json.dumps({"status": "accepted", "job_id": job_id, "message": "Job accepted."})

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 3: submit_work
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def submit_work(self, job_id: str, work_url: str, work_description: str) -> str:
        if job_id not in self.jobs:
            return json.dumps({"status": "error", "message": "Job not found."})
        job        = json.loads(self.jobs[job_id])
        freelancer = str(gl.message.sender_address)
        if job["freelancer"] != freelancer:
            return json.dumps({"status": "error", "message": "Only the assigned freelancer can submit."})
        if job["status"] != "IN_PROGRESS":
            return json.dumps({"status": "error", "message": "Job is not in progress."})
        job["work_url"]   = work_url
        job["work_desc"]  = work_description
        job["status"]     = "UNDER_REVIEW"
        self.jobs[job_id] = json.dumps(job)
        return json.dumps({"status": "submitted", "job_id": job_id, "message": "Work submitted."})

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 4: approve_work
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def approve_work(self, job_id: str) -> str:
        if job_id not in self.jobs:
            return json.dumps({"status": "error", "message": "Job not found."})
        job    = json.loads(self.jobs[job_id])
        client = str(gl.message.sender_address)
        if job["client"] != client:
            return json.dumps({"status": "error", "message": "Only the client can approve."})
        if job["status"] != "UNDER_REVIEW":
            return json.dumps({"status": "error", "message": "No work submitted for review."})
        escrow = json.loads(self.escrow[job_id])
        amt    = escrow["amount"]
        job["status"]       = "COMPLETED"
        escrow["released"]  = amt
        self.jobs[job_id]   = json.dumps(job)
        self.escrow[job_id] = json.dumps(escrow)
        self._inc_rep(job["freelancer"], "completed")
        self._init_rep(client)
        return json.dumps({"status": "completed", "job_id": job_id, "paid": amt})

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 5: request_mediation
    # VALIDATOR CALL 2 — AI Mediation
    # Pattern: prompt_comparative
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def request_mediation(self, job_id: str, issue: str) -> str:
        if job_id not in self.jobs:
            return json.dumps({"status": "error", "message": "Job not found."})
        job       = json.loads(self.jobs[job_id])
        requester = str(gl.message.sender_address)
        if requester not in [job["client"], job["freelancer"]]:
            return json.dumps({"status": "error", "message": "Only job parties can request mediation."})
        if job["status"] not in ["UNDER_REVIEW", "IN_PROGRESS"]:
            return json.dumps({"status": "error", "message": "Job is not in a mediatable state."})

        requester_role = "CLIENT" if requester == job["client"] else "FREELANCER"
        job_title  = job["title"]
        job_req    = job["requirements"]
        job_budget = job["budget"]

        # VALIDATOR CALL 2: prompt_comparative — Bradbury production pattern
        def mediate():
            prompt = (
                "You are an AI Mediator. Suggest a fair compromise.\n\n"
                "Job: " + job_title + "\n"
                "Requirements: " + job_req + "\n"
                "Budget: " + str(job_budget) + " GEN\n"
                "Issue raised by " + requester_role + ": " + issue + "\n\n"
                "Respond ONLY with valid JSON:\n"
                "{\"compromise_summary\": \"1-2 sentences\", "
                "\"client_should\": \"specific action\", "
                "\"freelancer_should\": \"specific action\", "
                "\"suggested_payment_pct\": 0-100, "
                "\"rationale\": \"why this is fair\"}\n\n"
                "No extra text."
            )
            result = gl.nondet.exec_prompt(prompt, response_format='json')
            return json.dumps(result, sort_keys=True)

        raw = gl.eq_principle.prompt_comparative(
            mediate,
            "suggested_payment_pct must be within 15 points; both must favor the same party"
        )

        try:
            md = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(md, dict):
                md = {}
        except Exception:
            md = {}

        return json.dumps({
            "status":                "mediation_complete",
            "job_id":                job_id,
            "compromise":            md.get("compromise_summary", ""),
            "client_should":         md.get("client_should", ""),
            "freelancer_should":     md.get("freelancer_should", ""),
            "suggested_payment_pct": md.get("suggested_payment_pct", 50),
            "rationale":             md.get("rationale", ""),
            "message": "AI mediators reached consensus. Accept or proceed to file_dispute."
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 6: file_dispute  ← CORE AI MECHANIC
    # VALIDATOR CALL 3 — 5 validators independently judge
    # Pattern: prompt_comparative
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
        job      = json.loads(self.jobs[job_id])
        filed_by = str(gl.message.sender_address)
        if filed_by not in [job["client"], job["freelancer"]]:
            return json.dumps({"status": "error", "message": "Only job parties can file a dispute."})
        if job["status"] not in ["UNDER_REVIEW", "IN_PROGRESS"]:
            return json.dumps({"status": "error", "message": "Job is not in a disputable state."})

        # Build reputation context
        client_rep = json.loads(self.reputations.get(job["client"], "{}")) if job["client"] in self.reputations else {}
        fl_rep     = json.loads(self.reputations.get(job["freelancer"], "{}")) if job["freelancer"] in self.reputations else {}
        client_score = _rep_score(client_rep.get("completed",0), client_rep.get("won",0), client_rep.get("lost",0), client_rep.get("bad_faith",0))
        fl_score     = _rep_score(fl_rep.get("completed",0), fl_rep.get("won",0), fl_rep.get("lost",0), fl_rep.get("bad_faith",0))

        # Build precedent context
        case_law   = json.loads(self.case_law)
        precedents = [c for c in case_law if c.get("category") == job["category"]][-3:]
        prec_text  = ""
        if precedents:
            prec_text = "PRECEDENTS:\n"
            for p in precedents:
                prec_text += "- " + p.get("summary","") + " -> " + str(p.get("verdict_pct","?")) + "% to freelancer\n"

        criteria = _category_criteria(job["category"])

        job_title  = job["title"]
        job_cat    = job["category"]
        job_budget = job["budget"]
        job_req    = job["requirements"]
        job_url    = job.get("work_url") or "Not provided"
        job_desc   = job.get("work_desc") or "Not provided"

        # VALIDATOR CALL 3: prompt_comparative — Bradbury production pattern
        def judge():
            prompt = (
                "GENLAYER COURT OF THE INTERNET\n"
                "You are a judge. Issue a GRADUATED VERDICT.\n\n"
                "Job: " + job_title + " (" + job_cat + ")\n"
                "Budget: " + str(job_budget) + " GEN\n\n"
                "REQUIREMENTS:\n" + job_req + "\n\n"
                "SUBMITTED WORK:\n"
                "URL: " + job_url + "\n"
                "Description: " + job_desc + "\n\n"
                "CLIENT EVIDENCE:\n" + client_evidence + "\n\n"
                "FREELANCER EVIDENCE:\n" + freelancer_evidence + "\n\n"
                "REPUTATION:\n"
                "Client: " + str(client_score) + "/100 (" + _rep_label(client_score) + ")\n"
                "Freelancer: " + str(fl_score) + "/100 (" + _rep_label(fl_score) + ")\n\n"
                + prec_text + "\n"
                + criteria + "\n"
                "Verdict guide:\n"
                "0=Freelancer failed completely\n"
                "25=Mostly failed, minor credit\n"
                "50=Genuinely disputed\n"
                "75=Mostly completed, minor shortfalls\n"
                "100=Fully completed, client unreasonable\n\n"
                "Respond ONLY with valid JSON:\n"
                "{\"verdict_pct\": 0 or 25 or 50 or 75 or 100, "
                "\"reasoning\": \"2-3 sentences\", "
                "\"key_factor\": \"most decisive factor\", "
                "\"confidence\": 0-100, "
                "\"precedent_applied\": true or false}\n\n"
                "No extra text."
            )
            result = gl.nondet.exec_prompt(prompt, response_format='json')
            return json.dumps(result, sort_keys=True)

        raw = gl.eq_principle.prompt_comparative(
            judge,
            "verdict_pct must be within 25 points and favor the same party (both >= 50 or both < 50)"
        )

        try:
            vd = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(vd, dict):
                vd = {}
        except Exception:
            vd = {}

        verdict_pct  = _nearest_verdict(int(vd.get("verdict_pct", 50)))
        reasoning    = str(vd.get("reasoning", ""))
        key_factor   = str(vd.get("key_factor", ""))
        confidence   = int(vd.get("confidence", 75))
        prec_applied = bool(vd.get("precedent_applied", False))

        total              = int(job["budget"])
        freelancer_payment = int(total * verdict_pct / 100)
        client_refund      = total - freelancer_payment

        self.dispute_counter = str(int(self.dispute_counter) + 1)
        dispute_id = "dispute_" + str(int(self.dispute_counter))

        self.disputes[dispute_id] = json.dumps({
            "job_id":              job_id,
            "filed_by":            filed_by,
            "client_evidence":     client_evidence,
            "freelancer_evidence": freelancer_evidence,
            "verdict_pct":         verdict_pct,
            "reasoning":           reasoning,
            "key_factor":          key_factor,
            "confidence":          confidence,
            "precedent_applied":   prec_applied,
            "freelancer_payment":  freelancer_payment,
            "client_refund":       client_refund,
            "status":              "RESOLVED",
            "appeal_count":        0,
            "appeal_upheld":       False,
            "appeal_reasoning":    "",
            "final_verdict_pct":   verdict_pct
        })

        job["status"]       = "DISPUTE_RESOLVED"
        self.jobs[job_id]   = json.dumps(job)
        escrow = json.loads(self.escrow[job_id])
        escrow["released"]  = freelancer_payment
        escrow["refunded"]  = client_refund
        self.escrow[job_id] = json.dumps(escrow)

        if verdict_pct >= 50:
            self._inc_rep(job["freelancer"], "won")
            self._inc_rep(job["client"],     "lost")
        else:
            self._inc_rep(job["client"],     "won")
            self._inc_rep(job["freelancer"], "lost")

        case_law.append({
            "dispute_id":  dispute_id,
            "category":    job["category"],
            "verdict_pct": verdict_pct,
            "confidence":  confidence,
            "summary":     job["title"][:60] + " | " + key_factor[:60]
        })
        if len(case_law) > 25:
            case_law = case_law[-25:]
        self.case_law = json.dumps(case_law)

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
            "message": "5 GenLayer validators reached consensus."
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 7: appeal_verdict
    # VALIDATOR CALL 4 — Court of Appeals
    # Pattern: prompt_comparative
    # ══════════════════════════════════════════════════════════════════════
    @gl.public.write
    def appeal_verdict(self, dispute_id: str, appeal_reason: str) -> str:
        if dispute_id not in self.disputes:
            return json.dumps({"status": "error", "message": "Dispute not found."})
        dispute = json.loads(self.disputes[dispute_id])
        if dispute["status"] != "RESOLVED":
            return json.dumps({"status": "error", "message": "Dispute is not appealable."})
        if int(dispute["appeal_count"]) >= 1:
            return json.dumps({"status": "error", "message": "Maximum one appeal. Verdict is final."})

        job_id = dispute["job_id"]
        job    = json.loads(self.jobs[job_id]) if job_id in self.jobs else {}

        d_verdict   = dispute["verdict_pct"]
        d_reasoning = dispute["reasoning"]
        d_key       = dispute.get("key_factor", "")
        job_title   = job.get("title", "")
        job_cat     = job.get("category", "")
        job_req     = job.get("requirements", "")
        d_client_ev = dispute["client_evidence"]
        d_fl_ev     = dispute["freelancer_evidence"]

        # VALIDATOR CALL 4: prompt_comparative — Bradbury production pattern
        def appellate_review():
            prompt = (
                "GENLAYER COURT OF APPEALS\n"
                "You are a SENIOR APPELLATE JUDGE.\n"
                "Only overturn if the original verdict was CLEARLY wrong.\n\n"
                "Job: " + job_title + " (" + job_cat + ")\n"
                "Requirements: " + job_req + "\n\n"
                "Client evidence: " + d_client_ev + "\n"
                "Freelancer evidence: " + d_fl_ev + "\n\n"
                "Original verdict: " + str(d_verdict) + "% to freelancer\n"
                "Original reasoning: " + d_reasoning + "\n"
                "Key factor: " + d_key + "\n\n"
                "Appeal argument: " + appeal_reason + "\n\n"
                "Respond ONLY with valid JSON:\n"
                "{\"upheld\": true or false, "
                "\"new_verdict_pct\": 0 or 25 or 50 or 75 or 100, "
                "\"appellate_reasoning\": \"2-3 sentences\", "
                "\"confidence\": 0-100}\n\n"
                "upheld=true: original stands. upheld=false: overturned.\n"
                "No extra text."
            )
            result = gl.nondet.exec_prompt(prompt, response_format='json')
            return json.dumps(result, sort_keys=True)

        raw = gl.eq_principle.prompt_comparative(
            appellate_review,
            "upheld field must match; if overturning, new_verdict_pct within 25 points"
        )

        try:
            ad = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(ad, dict):
                ad = {}
        except Exception:
            ad = {}

        upheld    = bool(ad.get("upheld", True))
        new_pct   = _nearest_verdict(int(ad.get("new_verdict_pct", d_verdict)))
        reasoning = str(ad.get("appellate_reasoning", ""))
        confidence= int(ad.get("confidence", 85))
        final_pct = d_verdict if upheld else new_pct

        dispute["appeal_count"]      = 1
        dispute["appeal_upheld"]     = upheld
        dispute["appeal_reasoning"]  = reasoning
        dispute["final_verdict_pct"] = final_pct
        dispute["status"]            = "APPEAL_FINAL"

        if not upheld and job:
            total          = int(job.get("budget", 0))
            new_fl_payment = int(total * final_pct / 100)
            new_cl_refund  = total - new_fl_payment
            dispute["freelancer_payment"] = new_fl_payment
            dispute["client_refund"]      = new_cl_refund
            if job_id in self.escrow:
                escrow = json.loads(self.escrow[job_id])
                escrow["released"]  = new_fl_payment
                escrow["refunded"]  = new_cl_refund
                self.escrow[job_id] = json.dumps(escrow)

        self.disputes[dispute_id] = json.dumps(dispute)

        return json.dumps({
            "status":              "appeal_final",
            "dispute_id":          dispute_id,
            "upheld":              upheld,
            "final_verdict_pct":   final_pct,
            "appellate_reasoning": reasoning,
            "confidence":          confidence,
            "freelancer_payment":  dispute["freelancer_payment"],
            "client_refund":       dispute["client_refund"],
            "message": "Court of Appeals has ruled. No further appeals."
        })

    # ══════════════════════════════════════════════════════════════════════
    # WRITE METHOD 8: verify_milestone
    # VALIDATOR CALL 5 — Milestone verification
    # Pattern: prompt_comparative
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
        job    = json.loads(self.jobs[job_id])
        client = str(gl.message.sender_address)
        if job["client"] != client:
            return json.dumps({"status": "error", "message": "Only the client can verify milestones."})
        if job["status"] not in ["IN_PROGRESS", "UNDER_REVIEW"]:
            return json.dumps({"status": "error", "message": "Job is not active."})

        criteria  = _category_criteria(job["category"])
        job_title = job["title"]
        job_cat   = job["category"]
        job_req   = job["requirements"]

        # VALIDATOR CALL 5: prompt_comparative — Bradbury production pattern
        def verify():
            prompt = (
                "You are a milestone evaluator.\n\n"
                "Job: " + job_title + " (" + job_cat + ")\n"
                "Overall requirements: " + job_req + "\n\n"
                "Milestone: " + milestone_desc + "\n"
                "Budget: " + str(milestone_budget) + " GEN\n\n"
                "Deliverable: " + freelancer_deliverable + "\n\n"
                + criteria + "\n"
                "Respond ONLY with valid JSON:\n"
                "{\"completed\": true or false, "
                "\"quality_score\": 0-100, "
                "\"feedback\": \"specific actionable feedback\"}\n\n"
                "No extra text."
            )
            result = gl.nondet.exec_prompt(prompt, response_format='json')
            return json.dumps(result, sort_keys=True)

        raw = gl.eq_principle.prompt_comparative(
            verify,
            "completed field must match; quality_score within 20 points"
        )

        try:
            mv = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(mv, dict):
                mv = {}
        except Exception:
            mv = {}

        completed = bool(mv.get("completed", False))
        quality   = int(mv.get("quality_score", 50))
        feedback  = str(mv.get("feedback", ""))

        job["milestones"].append({
            "description": milestone_desc,
            "budget":      milestone_budget,
            "completed":   completed,
            "quality":     quality,
            "feedback":    feedback
        })
        self.jobs[job_id] = json.dumps(job)

        return json.dumps({
            "status":           "milestone_verified",
            "completed":        completed,
            "quality_score":    quality,
            "feedback":         feedback,
            "payment_released": milestone_budget if completed else 0,
            "message": ("Milestone approved. " + str(milestone_budget) + " GEN released.") if completed else ("Milestone not completed. " + feedback)
        })

    # ══════════════════════════════════════════════════════════════════════
    # READ METHODS
    # ══════════════════════════════════════════════════════════════════════

    @gl.public.view
    def get_job(self, job_id: str) -> str:
        if job_id not in self.jobs:
            return json.dumps({"error": "Job not found."})
        return self.jobs[job_id]

    @gl.public.view
    def get_dispute(self, dispute_id: str) -> str:
        if dispute_id not in self.disputes:
            return json.dumps({"error": "Dispute not found."})
        return self.disputes[dispute_id]

    @gl.public.view
    def get_reputation(self, address: str) -> str:
        if address not in self.reputations:
            return json.dumps({"address": address, "score": 50, "label": "NEUTRAL",
                               "completed": 0, "won": 0, "lost": 0, "bad_faith": 0})
        rep   = json.loads(self.reputations[address])
        score = _rep_score(rep.get("completed",0), rep.get("won",0), rep.get("lost",0), rep.get("bad_faith",0))
        return json.dumps({
            "address":   address,
            "score":     score,
            "label":     _rep_label(score),
            "completed": rep.get("completed",0),
            "won":       rep.get("won",0),
            "lost":      rep.get("lost",0),
            "bad_faith": rep.get("bad_faith",0)
        })

    @gl.public.view
    def get_case_law(self, category: str) -> str:
        case_law = json.loads(self.case_law)
        if category.upper() == "ALL":
            return json.dumps(case_law)
        return json.dumps([c for c in case_law if c.get("category","") == category.upper()])

    @gl.public.view
    def get_all_jobs(self) -> str:
        result = {}
        for job_id, job_json in self.jobs.items():
            job = json.loads(job_json)
            result[job_id] = {
                "client":   job["client"],
                "title":    job["title"],
                "category": job["category"],
                "budget":   job["budget"],
                "status":   job["status"]
            }
        return json.dumps(result)

    @gl.public.view
    def get_all_disputes(self) -> str:
        result = {}
        for did, d_json in self.disputes.items():
            d = json.loads(d_json)
            result[did] = {
                "job_id":      d["job_id"],
                "verdict_pct": d["verdict_pct"],
                "status":      d["status"]
            }
        return json.dumps(result)

    @gl.public.view
    def get_platform_stats(self) -> str:
        completed_jobs = 0
        total_volume   = 0
        resolved       = 0
        for job_json in self.jobs.values():
            job = json.loads(job_json)
            if job["status"] == "COMPLETED":
                completed_jobs += 1
            total_volume += int(job["budget"])
        for d_json in self.disputes.values():
            d = json.loads(d_json)
            if "RESOLVED" in d["status"] or "FINAL" in d["status"]:
                resolved += 1
        return json.dumps({
            "total_jobs":        len(self.jobs),
            "completed_jobs":    completed_jobs,
            "total_disputes":    len(self.disputes),
            "resolved_disputes": resolved,
            "total_volume_gen":  total_volume,
            "case_law_entries":  len(json.loads(self.case_law))
        })

    # ══════════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════════

    def _init_rep(self, address: str):
        if address not in self.reputations:
            self.reputations[address] = json.dumps({
                "completed": 0, "won": 0, "lost": 0, "bad_faith": 0
            })

    def _inc_rep(self, address: str, field: str):
        self._init_rep(address)
        rep = json.loads(self.reputations[address])
        rep[field] = rep.get(field, 0) + 1
        self.reputations[address] = json.dumps(rep)
