'use client'
import React, { useState, useEffect, useCallback } from 'react'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount } from 'wagmi'
import { readContract } from '@/lib/genlayer'
import { CONTRACT_ADDRESS } from '@/lib/config'

interface Job {
  job_id: string; client: string; client_wallet: string
  worker: string; worker_wallet: string; title: string
  description: string; requirements: string; budget: string
  category: string; status: string; feasibility: string
  feasibility_score: string; work_submission: string
  submission_description: string; ai_score: string
  ai_score_reasoning: string; payment_pct: string
  payment_due: string; payment_proof: string
  payment_confirmed: string; mediation_suggestion: string
  milestone_count: string; milestones_completed: string
  _has_score?: string
}

interface Dispute {
  dispute_id: string; job_id: string; filer: string
  defendant: string; grounds: string; verdict_pct: string
  verdict_reasoning: string; appeal_verdict_pct: string
  appeal_reasoning: string; status: string; category: string
}

interface Reputation {
  score: string; jobs_completed_as_worker: string
  jobs_completed_as_client: string; jobs_scored_well: string
  disputes_won: string; disputes_lost: string
  total_disputes: string; payment_defaults: string
}

interface Profile { name: string; bio: string; avatar: string }

type Tab = 'jobs' | 'disputes' | 'caselaw' | 'dashboard'
type CatFilter = 'ALL' | 'Web Development' | 'Smart Contract Development' | 'Writing & Content' | 'Data & Analytics' | 'Marketing & SEO' | 'Research & Reports'
type StatusFilter = 'ALL' | 'OPEN' | 'ACCEPTED' | 'SCORED' | 'PAID' | 'RESOLVED'

const ORANGE = '#E8660A', DARK = '#0A0A0A', CARD = '#111111', BORDER = '#222222'
const TEXT = '#F0F0F0', MUTED = '#555555', SUCCESS = '#22c55e', DANGER = '#ef4444'
const WARNING = '#f59e0b', PURPLE = '#a78bfa'

const SUPPORTED_CATEGORIES = [
  'Web Development', 'Smart Contract Development', 'Writing & Content',
  'Data & Analytics', 'Marketing & SEO', 'Research & Reports',
] as const

const CAT_SHORT: Record<string, string> = {
  'ALL': 'ALL', 'Web Development': 'Web Dev',
  'Smart Contract Development': 'Smart Contract', 'Writing & Content': 'Writing',
  'Data & Analytics': 'Data', 'Marketing & SEO': 'Marketing', 'Research & Reports': 'Research',
}

const STATUS_LABEL: Record<string, string> = {
  OPEN: 'Open', ACCEPTED: 'In Progress', SCORED: 'AI Scored',
  PAID: 'Paid', RESOLVED: 'Resolved', CANCELLED: 'Cancelled',
}

const STATUS_COLOR: Record<string, string> = {
  OPEN: ORANGE, ACCEPTED: '#60a5fa', SCORED: WARNING,
  PAID: SUCCESS, RESOLVED: MUTED, CANCELLED: DANGER,
}

function shortAddr(a: string) {
  if (!a || a === '0x0000000000000000000000000000000000000000') return '—'
  return `${a.slice(0, 6)}…${a.slice(-4)}`
}

function scoreColor(n: number) {
  if (n >= 85) return SUCCESS; if (n >= 60) return '#86efac'
  if (n >= 40) return WARNING; if (n >= 20) return ORANGE
  return DANGER
}

function budgetDisplay(b: string) {
  if (!b) return '—'
  return b.toUpperCase().includes('GEN') ? b : b + ' GEN'
}

const inputStyle: React.CSSProperties = {
  width: '100%', backgroundColor: '#0a0a0a', border: `1px solid ${BORDER}`,
  borderRadius: '8px', padding: '10px 12px', color: TEXT, fontSize: '13px',
  boxSizing: 'border-box', outline: 'none',
}

export default function Home() {
  const { address } = useAccount()
  const [tab, setTab] = useState<Tab>('jobs')
  const [jobs, setJobs] = useState<Job[]>([])
  const [disputes, setDisputes] = useState<Dispute[]>([])
  const [stats, setStats] = useState<Record<string, string>>({})
  const [reputation, setReputation] = useState<Reputation | null>(null)
  const [profile, setProfile] = useState<Profile>({ name: '', bio: '', avatar: '' })
  const [editingProfile, setEditingProfile] = useState(false)
  const [profileDraft, setProfileDraft] = useState<Profile>({ name: '', bio: '', avatar: '' })
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [msg, setMsg] = useState<{ text: string; error: boolean } | null>(null)
  const [showPostModal, setShowPostModal] = useState(false)
  const [submitWorkModal, setSubmitWorkModal] = useState<{ jobId: string; title: string; requirements: string } | null>(null)
  const [catFilter, setCatFilter] = useState<CatFilter>('ALL')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')

  const fetchAll = useCallback(async () => {
    setRefreshing(true)
    const delay = (ms: number) => new Promise(r => setTimeout(r, ms))
    try {
      const jobsRaw = await readContract('get_all_jobs')
      try { setJobs(JSON.parse(jobsRaw as string)) } catch {}
      await delay(700)
      const disputesRaw = await readContract('get_all_disputes')
      try { setDisputes(JSON.parse(disputesRaw as string)) } catch {}
      await delay(700)
      const statsRaw = await readContract('get_platform_stats')
      try { setStats(JSON.parse(statsRaw as string)) } catch {}
    } catch (e) { console.error('Fetch error:', e) }
    finally { setRefreshing(false) }
  }, [])

  const fetchReputation = useCallback(async (addr: string) => {
    try {
      const raw = await readContract('get_reputation', [addr])
      setReputation(JSON.parse(raw as string))
    } catch {}
  }, [])

  const fetchPrivateJobData = useCallback(async (jobId: string, viewer: string): Promise<Job | null> => {
    try {
      const raw = await readContract('get_job_for_party', [jobId, viewer])
      return JSON.parse(raw as string)
    } catch { return null }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  useEffect(() => {
    if (!address) return
    try {
      const saved = localStorage.getItem(`arbitrex_profile_${address}`)
      if (saved) { const p = JSON.parse(saved); setProfile(p); setProfileDraft(p) }
    } catch {}
    fetchReputation(address)
  }, [address, fetchReputation])

  const showMsg = (text: string, error = false) => {
    setMsg({ text, error })
    if (!error) setTimeout(() => setMsg(null), 12000)
  }

  async function callWrite(method: string, args: unknown[]) {
    if (!address) { showMsg('Connect your wallet first.', true); return false }
    setLoading(true)
    showMsg(`Submitting ${method}…${method === 'submit_work' ? ' AI validators are scoring your work. This takes 1–3 minutes. Do not close this tab.' : ' Processing…'}`)
    try {
      const { writeContractWithWallet } = await import('@/lib/genlayer')
      const result = await writeContractWithWallet(address, method, args)
      setLoading(false)
      if (result.success) {
        showMsg(`✓ ${method} succeeded.\nTx: ${result.txHash?.slice(0, 24)}…`)
        await fetchAll()
        if (address) await fetchReputation(address)
        return true
      } else {
        showMsg(`Transaction failed:\n${result.error}`, true)
        return false
      }
    } catch (e: any) {
      setLoading(false)
      showMsg(e?.message ?? String(e), true)
      return false
    }
  }

  const filteredJobs = jobs.filter(j => {
    if (catFilter !== 'ALL' && j.category !== catFilter) return false
    if (statusFilter !== 'ALL' && j.status !== statusFilter) return false
    return true
  })

  const myPostedJobs = jobs.filter(j => j.client === address)
  const myWorkerJobs = jobs.filter(j => j.worker === address)
  const myDisputes = disputes.filter(d => d.filer === address || d.defendant === address)

  function saveProfile() {
    setProfile(profileDraft)
    try { localStorage.setItem(`arbitrex_profile_${address}`, JSON.stringify(profileDraft)) } catch {}
    setEditingProfile(false)
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: DARK, color: TEXT, fontFamily: "'Inter',system-ui,sans-serif" }}>
      <nav style={{ position: 'sticky', top: 0, zIndex: 100, backgroundColor: '#0D0D0D', borderBottom: `1px solid ${BORDER}`, padding: '0 20px', display: 'flex', alignItems: 'center', height: '56px', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <div style={{ width: '28px', height: '28px', backgroundColor: ORANGE, borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}>⚖️</div>
          <span style={{ fontWeight: 700, fontSize: '16px' }}>ArbitrEx</span>
        </div>
        <div style={{ display: 'flex', gap: '2px', flex: 1, overflowX: 'auto' }}>
          {(['jobs', 'disputes', 'caselaw', 'dashboard'] as Tab[]).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{ padding: '6px 12px', borderRadius: '6px', border: 'none', cursor: 'pointer', fontSize: '13px', fontWeight: 500, backgroundColor: tab === t ? '#1a1a1a' : 'transparent', color: tab === t ? TEXT : MUTED, whiteSpace: 'nowrap', flexShrink: 0 }}>
              {t === 'jobs' ? 'Jobs' : t === 'disputes' ? 'Disputes' : t === 'caselaw' ? 'Case Law' : 'Dashboard'}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <button onClick={() => setShowPostModal(true)} style={{ backgroundColor: ORANGE, color: '#fff', border: 'none', borderRadius: '8px', padding: '7px 14px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}>+ Post Job</button>
          <ConnectButton showBalance={false} chainStatus="none" accountStatus="avatar" />
        </div>
      </nav>

      {msg && (
        <div onClick={() => setMsg(null)} style={{ position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 200, backgroundColor: msg.error ? '#1a0505' : '#051a0a', border: `1px solid ${msg.error ? DANGER : SUCCESS}`, borderRadius: '12px 12px 0 0', padding: '14px 20px', cursor: 'pointer' }}>
          <pre style={{ fontSize: '12px', fontFamily: 'monospace', color: msg.error ? '#f87171' : '#4ade80', whiteSpace: 'pre-wrap', margin: 0 }}>{msg.text}</pre>
          <p style={{ fontSize: '10px', color: MUTED, marginTop: '4px' }}>Tap to dismiss</p>
        </div>
      )}

      {showPostModal && <PostJobModal onClose={() => setShowPostModal(false)} onSubmit={callWrite} loading={loading} />}
      {submitWorkModal && <SubmitWorkModal job={submitWorkModal} onClose={() => setSubmitWorkModal(null)} onSubmit={callWrite} loading={loading} />}

      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 20px' }}>

        {tab === 'jobs' && (
          <div>
            <div style={{ margin: '16px 0', backgroundColor: CARD, borderRadius: '14px', padding: 'clamp(20px,4vw,48px)', backgroundImage: 'radial-gradient(ellipse at 75% 50%, rgba(232,102,10,0.10) 0%, transparent 65%)', border: `1px solid ${BORDER}` }}>
              <p style={{ fontSize: '12px', color: ORANGE, fontWeight: 600, marginBottom: '10px' }}>⚖️ Powered by GenLayer AI Validators</p>
              <h1 style={{ fontSize: 'clamp(22px,5vw,46px)', fontWeight: 700, lineHeight: 1.1, marginBottom: '12px' }}>The Court of the Internet<br /><span style={{ color: ORANGE }}>for Freelance Work</span></h1>
              <p style={{ color: MUTED, fontSize: 'clamp(13px,2vw,15px)', maxWidth: '500px', lineHeight: 1.6, marginBottom: '20px' }}>Post jobs, submit work, and let 5 independent GenLayer validators score the delivery. No human judges. No bias. Payment verdicts in minutes.</p>
              <button onClick={() => setShowPostModal(true)} style={{ backgroundColor: ORANGE, color: '#fff', border: 'none', borderRadius: '10px', padding: '12px 24px', fontSize: '15px', fontWeight: 600, cursor: 'pointer' }}>+ Post a Job</button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', margin: '16px 0' }}>
              <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '2px' }}>
                {(['ALL', ...SUPPORTED_CATEGORIES] as CatFilter[]).map(c => (
                  <button key={c} onClick={() => setCatFilter(c)} style={{ padding: '5px 14px', borderRadius: '20px', border: `1px solid ${catFilter === c ? ORANGE : BORDER}`, backgroundColor: catFilter === c ? ORANGE : 'transparent', color: catFilter === c ? '#fff' : MUTED, fontSize: '12px', fontWeight: catFilter === c ? 600 : 400, cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0 }}>
                    {CAT_SHORT[c] ?? c}
                  </button>
                ))}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                <div style={{ display: 'flex', gap: '6px', overflowX: 'auto' }}>
                  {(['ALL', 'OPEN', 'ACCEPTED', 'SCORED', 'PAID'] as StatusFilter[]).map(s => (
                    <button key={s} onClick={() => setStatusFilter(s)} style={{ padding: '5px 12px', borderRadius: '20px', border: `1px solid ${statusFilter === s ? '#fff' : BORDER}`, backgroundColor: statusFilter === s ? '#1c1c1c' : 'transparent', color: statusFilter === s ? TEXT : MUTED, fontSize: '12px', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0 }}>
                      {s === 'ALL' ? 'All Status' : STATUS_LABEL[s]}
                    </button>
                  ))}
                </div>
                <button onClick={fetchAll} style={{ padding: '5px 14px', borderRadius: '20px', border: `1px solid ${BORDER}`, backgroundColor: 'transparent', color: MUTED, fontSize: '12px', cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0 }}>{refreshing ? '↻ Loading…' : '↻ Refresh'}</button>
              </div>
            </div>

            <div style={{ marginBottom: '14px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 600 }}>Available Jobs</h2>
              <p style={{ color: MUTED, fontSize: '13px', marginTop: '2px' }}>{filteredJobs.length} job{filteredJobs.length !== 1 ? 's' : ''} found</p>
            </div>

            {filteredJobs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', backgroundColor: CARD, borderRadius: '12px', border: `1px solid ${BORDER}` }}>
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>💼</div>
                <p style={{ fontSize: '16px', fontWeight: 600, marginBottom: '6px' }}>No jobs found</p>
                <p style={{ color: MUTED, fontSize: '13px' }}>Try a different filter or post the first job</p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(340px,100%), 1fr))', gap: '14px', paddingBottom: '48px' }}>
                {filteredJobs.map(job => (
                  <JobCard key={job.job_id} job={job} address={address} onAction={callWrite} loading={loading}
                    onOpenSubmit={(id, title, req) => setSubmitWorkModal({ jobId: id, title, requirements: req })}
                    fetchPrivate={fetchPrivateJobData} />
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'disputes' && (
          <div style={{ paddingTop: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div><h2 style={{ fontSize: '24px', fontWeight: 700 }}>Disputes</h2><p style={{ color: MUTED, fontSize: '13px', marginTop: '2px' }}>{disputes.length} total</p></div>
              <button onClick={fetchAll} style={{ padding: '6px 14px', borderRadius: '20px', border: `1px solid ${BORDER}`, backgroundColor: 'transparent', color: MUTED, fontSize: '12px', cursor: 'pointer' }}>{refreshing ? '↻ Loading…' : '↻ Refresh'}</button>
            </div>
            {disputes.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px', backgroundColor: CARD, borderRadius: '12px', border: `1px solid ${BORDER}` }}>
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>⚖️</div>
                <p style={{ fontSize: '16px', fontWeight: 600 }}>No disputes yet</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {disputes.map(d => <DisputeCard key={d.dispute_id} dispute={d} address={address} onAction={callWrite} loading={loading} />)}
              </div>
            )}
          </div>
        )}

        {tab === 'caselaw' && (
          <div style={{ paddingTop: '24px' }}>
            <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '8px' }}>On-Chain Case Law</h2>
            <p style={{ color: MUTED, fontSize: '14px', marginBottom: '24px', maxWidth: '560px', lineHeight: 1.6 }}>Every AI scoring verdict becomes on-chain precedent. Validators consult past cases when scoring new work in the same category.</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px,1fr))', gap: '14px', marginBottom: '32px' }}>
              {SUPPORTED_CATEGORIES.map(cat => <CaseLawCard key={cat} category={cat} jobs={jobs} disputes={disputes} />)}
            </div>
            <div style={{ backgroundColor: CARD, border: `1px solid ${BORDER}`, borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px' }}>Payment Score Brackets</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {[{ min: 85, max: 100, pct: '100%', label: 'Full payment', color: SUCCESS },
                  { min: 60, max: 84, pct: '75%', label: '75% payment', color: '#86efac' },
                  { min: 40, max: 59, pct: '50%', label: '50/50 split', color: WARNING },
                  { min: 20, max: 39, pct: '25%', label: '25% payment', color: ORANGE },
                  { min: 0, max: 19, pct: '0%', label: 'No payment', color: DANGER }].map(b => (
                  <div key={b.pct} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '60px', height: '24px', backgroundColor: `${b.color}22`, border: `1px solid ${b.color}44`, borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: b.color }}>{b.pct}</span>
                    </div>
                    <div style={{ flex: 1, height: '6px', backgroundColor: '#1a1a1a', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ width: `${b.max}%`, height: '100%', backgroundColor: b.color, borderRadius: '3px' }} />
                    </div>
                    <span style={{ fontSize: '12px', color: MUTED, width: '80px', textAlign: 'right' }}>Score {b.min}–{b.max}</span>
                    <span style={{ fontSize: '12px', color: b.color, fontWeight: 500, width: '100px' }}>{b.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === 'dashboard' && (
          <div style={{ paddingTop: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div><h2 style={{ fontSize: '24px', fontWeight: 700 }}>Dashboard</h2><p style={{ color: MUTED, fontSize: '13px', fontFamily: 'monospace', marginTop: '2px' }}>{address ? shortAddr(address) : 'Connect wallet'}</p></div>
              <button onClick={fetchAll} style={{ padding: '6px 14px', borderRadius: '20px', border: `1px solid ${BORDER}`, backgroundColor: 'transparent', color: MUTED, fontSize: '12px', cursor: 'pointer' }}>{refreshing ? '↻ Loading…' : '↻ Refresh'}</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: '10px', marginBottom: '24px' }}>
              {[{ label: 'Total Jobs', value: stats.total_jobs ?? '0' },
                { label: 'Open Jobs', value: stats.open_jobs ?? '0' },
                { label: 'AI Scored', value: stats.scored_jobs ?? '0' },
                { label: 'Disputes', value: stats.total_disputes ?? '0' }].map(s => (
                <div key={s.label} style={{ backgroundColor: CARD, border: `1px solid ${BORDER}`, borderRadius: '10px', padding: '16px', textAlign: 'center' }}>
                  <p style={{ fontSize: '28px', fontWeight: 700, color: ORANGE }}>{s.value}</p>
                  <p style={{ fontSize: '11px', color: MUTED, marginTop: '2px' }}>{s.label}</p>
                </div>
              ))}
            </div>

            {!address ? (
              <div style={{ textAlign: 'center', padding: '48px', backgroundColor: CARD, borderRadius: '12px', border: `1px solid ${BORDER}` }}>
                <p style={{ fontSize: '16px', fontWeight: 600 }}>Connect your wallet</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

                {/* Profile Card */}
                <div style={{ backgroundColor: CARD, border: `1px solid ${BORDER}`, borderRadius: '12px', padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 600 }}>My Profile</h3>
                    {!editingProfile && <button onClick={() => { setProfileDraft(profile); setEditingProfile(true) }} style={{ backgroundColor: 'transparent', color: ORANGE, border: `1px solid ${ORANGE}55`, borderRadius: '8px', padding: '6px 12px', fontSize: '12px', cursor: 'pointer' }}>Edit Profile</button>}
                  </div>
                  {editingProfile ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div><label style={{ display: 'block', fontSize: '11px', color: MUTED, marginBottom: '4px' }}>Display Name</label><input value={profileDraft.name} onChange={e => setProfileDraft(p => ({ ...p, name: e.target.value }))} placeholder="Your name or pseudonym" style={inputStyle} /></div>
                      <div><label style={{ display: 'block', fontSize: '11px', color: MUTED, marginBottom: '4px' }}>Avatar URL</label><input value={profileDraft.avatar} onChange={e => setProfileDraft(p => ({ ...p, avatar: e.target.value }))} placeholder="https://... (image URL)" style={inputStyle} /></div>
                      <div><label style={{ display: 'block', fontSize: '11px', color: MUTED, marginBottom: '4px' }}>Bio</label><textarea value={profileDraft.bio} onChange={e => setProfileDraft(p => ({ ...p, bio: e.target.value }))} placeholder="Tell clients and workers about yourself..." style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }} /></div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button onClick={saveProfile} style={{ flex: 1, backgroundColor: ORANGE, color: '#fff', border: 'none', borderRadius: '8px', padding: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}>Save</button>
                        <button onClick={() => setEditingProfile(false)} style={{ backgroundColor: 'transparent', color: MUTED, border: `1px solid ${BORDER}`, borderRadius: '8px', padding: '10px', fontSize: '13px', cursor: 'pointer' }}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                      <div style={{ width: '72px', height: '72px', borderRadius: '50%', backgroundColor: '#1a1a1a', border: `2px solid ${ORANGE}55`, overflow: 'hidden', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '28px' }}>
                        {profile.avatar ? <img src={profile.avatar} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} /> : '👤'}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontWeight: 700, fontSize: '18px', marginBottom: '2px' }}>{profile.name || 'Anonymous'}</p>
                        <p style={{ fontSize: '11px', color: MUTED, fontFamily: 'monospace', marginBottom: '8px' }}>{shortAddr(address)}</p>
                        {profile.bio && <p style={{ fontSize: '13px', color: MUTED, lineHeight: 1.5, marginBottom: '12px' }}>{profile.bio}</p>}
                        {reputation && (
                          <>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '8px', marginBottom: '12px' }}>
                              {[
                                { label: 'Rep Score', value: reputation.score, color: ORANGE },
                                { label: 'Jobs as Worker', value: reputation.jobs_completed_as_worker, color: SUCCESS },
                                { label: 'Jobs as Client', value: reputation.jobs_completed_as_client, color: '#60a5fa' },
                                { label: 'High Scores', value: reputation.jobs_scored_well, color: '#86efac' },
                                { label: 'Disputes Won', value: reputation.disputes_won, color: SUCCESS },
                                { label: 'Disputes Lost', value: reputation.disputes_lost, color: DANGER },
                                { label: 'Pay Defaults', value: reputation.payment_defaults, color: parseInt(reputation.payment_defaults) > 0 ? DANGER : MUTED },
                                { label: 'Total Disputes', value: reputation.total_disputes, color: MUTED },
                              ].map(s => (
                                <div key={s.label} style={{ backgroundColor: '#0a0a0a', border: `1px solid ${BORDER}`, borderRadius: '8px', padding: '8px', textAlign: 'center' }}>
                                  <p style={{ fontSize: '18px', fontWeight: 700, color: s.color }}>{s.value}</p>
                                  <p style={{ fontSize: '9px', color: MUTED, marginTop: '2px' }}>{s.label}</p>
                                </div>
                              ))}
                            </div>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                <span style={{ fontSize: '11px', color: MUTED }}>Reputation</span>
                                <span style={{ fontSize: '11px', color: ORANGE, fontWeight: 600 }}>{reputation.score}/100</span>
                              </div>
                              <div style={{ backgroundColor: '#1a1a1a', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
                                <div style={{ width: `${Math.min(parseInt(reputation.score), 100)}%`, height: '100%', backgroundColor: ORANGE, borderRadius: '4px', transition: 'width 0.6s ease' }} />
                              </div>
                              <p style={{ fontSize: '10px', color: MUTED, marginTop: '4px' }}>
                                {parseInt(reputation.score) >= 80 ? '⭐ Excellent' : parseInt(reputation.score) >= 60 ? '👍 Good standing' : parseInt(reputation.score) >= 40 ? '⚠️ Average' : '❌ Poor — defaults and disputes affect this'}
                              </p>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>📋 Jobs I Posted <span style={{ fontSize: '13px', color: MUTED, fontWeight: 400 }}>({myPostedJobs.length})</span></h3>
                  {myPostedJobs.length === 0 ? (
                    <div style={{ backgroundColor: CARD, border: `1px solid ${BORDER}`, borderRadius: '10px', padding: '24px', textAlign: 'center', color: MUTED, fontSize: '13px' }}>
                      No jobs posted. <button onClick={() => setShowPostModal(true)} style={{ color: ORANGE, background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', fontSize: '13px' }}>Post your first job</button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {myPostedJobs.map(job => <JobCard key={job.job_id} job={job} address={address} onAction={callWrite} loading={loading} compact onOpenSubmit={(id, title, req) => setSubmitWorkModal({ jobId: id, title, requirements: req })} fetchPrivate={fetchPrivateJobData} />)}
                    </div>
                  )}
                </div>

                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>🔨 Jobs I'm Working On <span style={{ fontSize: '13px', color: MUTED, fontWeight: 400 }}>({myWorkerJobs.length})</span></h3>
                  {myWorkerJobs.length === 0 ? (
                    <div style={{ backgroundColor: CARD, border: `1px solid ${BORDER}`, borderRadius: '10px', padding: '24px', textAlign: 'center', color: MUTED, fontSize: '13px' }}>
                      No active jobs. <button onClick={() => setTab('jobs')} style={{ color: ORANGE, background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', fontSize: '13px' }}>Browse open jobs</button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {myWorkerJobs.map(job => <JobCard key={job.job_id} job={job} address={address} onAction={callWrite} loading={loading} compact onOpenSubmit={(id, title, req) => setSubmitWorkModal({ jobId: id, title, requirements: req })} fetchPrivate={fetchPrivateJobData} />)}
                    </div>
                  )}
                </div>

                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>⚖️ My Disputes <span style={{ fontSize: '13px', color: MUTED, fontWeight: 400 }}>({myDisputes.length})</span></h3>
                  {myDisputes.length === 0 ? (
                    <div style={{ backgroundColor: CARD, border: `1px solid ${BORDER}`, borderRadius: '10px', padding: '24px', textAlign: 'center', color: MUTED, fontSize: '13px' }}>No disputes filed</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {myDisputes.map(d => <DisputeCard key={d.dispute_id} dispute={d} address={address} onAction={callWrite} loading={loading} />)}
                    </div>
                  )}
                </div>

                <div style={{ backgroundColor: CARD, border: `1px solid ${BORDER}`, borderRadius: '10px', padding: '14px 16px', fontFamily: 'monospace', fontSize: '11px', color: MUTED, lineHeight: 1.8 }}>
                  <p>Contract: {CONTRACT_ADDRESS}</p>
                  <p>Network: GenLayer Bradbury Testnet · Chain ID: 4221</p>
                  <p><a href={`https://explorer-bradbury.genlayer.com/address/${CONTRACT_ADDRESS}`} target="_blank" rel="noopener" style={{ color: ORANGE, textDecoration: 'underline' }}>View on Explorer →</a></p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function JobCard({ job, address, onAction, loading, compact = false, onOpenSubmit, fetchPrivate }: {
  job: Job; address?: string
  onAction: (m: string, a: unknown[]) => Promise<boolean>
  loading: boolean; compact?: boolean
  onOpenSubmit?: (id: string, title: string, req: string) => void
  fetchPrivate?: (jobId: string, viewer: string) => Promise<Job | null>
}) {
  const isClient = job.client === address
  const isWorker = job.worker === address
  const isParty = isClient || isWorker
  const statusColor = STATUS_COLOR[job.status] ?? MUTED
  const [showDispute, setShowDispute] = useState(false)
  const [disputeGrounds, setDisputeGrounds] = useState('')
  const [showMediation, setShowMediation] = useState(false)
  const [mediationPos, setMediationPos] = useState('')
  const [showPaymentProof, setShowPaymentProof] = useState(false)
  const [paymentProof, setPaymentProof] = useState('')
  const [privateJob, setPrivateJob] = useState<Job | null>(null)
  const [loadingPrivate, setLoadingPrivate] = useState(false)

  // Fetch private data when party views a scored job
  useEffect(() => {
    if (!isParty || !address || !fetchPrivate) return
    if (job.status === 'SCORED' || job.status === 'PAID' || job.status === 'RESOLVED') {
      setLoadingPrivate(true)
      fetchPrivate(job.job_id, address).then(d => {
        setPrivateJob(d)
        setLoadingPrivate(false)
      })
    }
  }, [job.job_id, job.status, isParty, address, fetchPrivate])

  const displayJob = privateJob ?? job

  return (
    <div style={{ backgroundColor: CARD, border: `1px solid ${BORDER}`, borderRadius: '12px', padding: compact ? '14px' : '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <span style={{ fontSize: '10px', color: MUTED, fontFamily: 'monospace' }}>#{job.job_id}</span>
          <p style={{ fontWeight: 600, fontSize: compact ? '13px' : '15px', color: TEXT, marginTop: '2px', lineHeight: 1.3 }}>{job.title}</p>
        </div>
        <span style={{ fontSize: '10px', fontWeight: 600, color: statusColor, backgroundColor: `${statusColor}18`, padding: '3px 8px', borderRadius: '20px', whiteSpace: 'nowrap', flexShrink: 0 }}>
          {STATUS_LABEL[job.status] ?? job.status}
        </span>
      </div>

      {!compact && <p style={{ fontSize: '12px', color: MUTED, lineHeight: 1.5, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' as any }}>{job.description}</p>}

      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '10px', color: MUTED, backgroundColor: '#181818', border: `1px solid ${BORDER}`, borderRadius: '4px', padding: '2px 7px' }}>{job.category}</span>
        <span style={{ fontSize: '10px', color: ORANGE, backgroundColor: '#1a0a00', border: `1px solid ${BORDER}`, borderRadius: '4px', padding: '2px 7px', fontWeight: 500 }}>{budgetDisplay(job.budget)}</span>
        {job.feasibility && <span style={{ fontSize: '10px', color: job.feasibility === 'FEASIBLE' ? SUCCESS : DANGER, backgroundColor: '#0a1a0a', border: `1px solid ${BORDER}`, borderRadius: '4px', padding: '2px 7px' }}>AI: {job.feasibility} {job.feasibility_score}%</span>}
      </div>

      <div style={{ fontSize: '11px', color: MUTED, display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        <span>Client: <span style={{ fontFamily: 'monospace', color: isClient ? ORANGE : MUTED }}>{shortAddr(job.client)}{isClient ? ' (you)' : ''}</span></span>
        {job.worker !== '0x0000000000000000000000000000000000000000' && (
          <span>Worker: <span style={{ fontFamily: 'monospace', color: isWorker ? ORANGE : MUTED }}>{shortAddr(job.worker)}{isWorker ? ' (you)' : ''}</span></span>
        )}
      </div>

      {/* Work submission — private */}
      {isParty && displayJob.work_submission && (
        <div style={{ backgroundColor: '#051a0a', border: `1px solid ${SUCCESS}33`, borderRadius: '8px', padding: '10px' }}>
          <p style={{ fontSize: '10px', color: SUCCESS, fontWeight: 600, marginBottom: '6px' }}>📎 Work Submitted — Private</p>
          <a href={displayJob.work_submission.startsWith('http') ? displayJob.work_submission : '#'} target="_blank" rel="noopener" style={{ fontSize: '12px', color: '#60a5fa', wordBreak: 'break-all', textDecoration: 'underline' }}>{displayJob.work_submission}</a>
          {displayJob.submission_description && <p style={{ fontSize: '11px', color: MUTED, marginTop: '6px', lineHeight: 1.5 }}>{displayJob.submission_description}</p>}
        </div>
      )}
      {!isParty && job._has_score === 'true' && (
        <div style={{ backgroundColor: '#141414', border: `1px solid ${BORDER}`, borderRadius: '8px', padding: '8px 10px' }}>
          <p style={{ fontSize: '11px', color: MUTED }}>🔒 Work and score are private — visible to client and worker only</p>
        </div>
      )}

      {/* AI Score — private to parties */}
      {isParty && displayJob.ai_score && !loadingPrivate && (
        <div style={{ backgroundColor: '#0a0a14', border: `1px solid ${WARNING}44`, borderRadius: '10px', padding: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <p style={{ fontSize: '11px', color: WARNING, fontWeight: 600 }}>🤖 AI Validator Score</p>
            <span style={{ fontSize: '22px', fontWeight: 700, color: scoreColor(parseInt(displayJob.ai_score)), fontFamily: 'monospace' }}>{displayJob.ai_score}/100</span>
          </div>
          <p style={{ fontSize: '12px', color: MUTED, lineHeight: 1.5, marginBottom: '10px' }}>{displayJob.ai_score_reasoning}</p>

          {/* Payment verdict */}
          <div style={{ backgroundColor: '#0a0a0a', borderRadius: '8px', padding: '10px 12px', marginBottom: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: MUTED }}>Payment verdict:</span>
              <span style={{ fontSize: '16px', fontWeight: 700, color: displayJob.payment_pct === '0' ? DANGER : SUCCESS }}>{displayJob.payment_due || '—'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
              <span style={{ fontSize: '11px', color: MUTED }}>({displayJob.payment_pct}% of {displayJob.budget})</span>
            </div>
          </div>

          {/* Worker wallet — shown to client for payment */}
          {isClient && displayJob.payment_pct !== '0' && displayJob.worker_wallet && (
            <div style={{ backgroundColor: '#051a0a', border: `1px solid ${SUCCESS}44`, borderRadius: '8px', padding: '10px 12px' }}>
              <p style={{ fontSize: '11px', color: SUCCESS, fontWeight: 600, marginBottom: '4px' }}>💸 Send payment to this wallet:</p>
              <p style={{ fontSize: '12px', color: SUCCESS, fontFamily: 'monospace', wordBreak: 'break-all', fontWeight: 600 }}>{displayJob.worker_wallet}</p>
              <p style={{ fontSize: '10px', color: MUTED, marginTop: '4px' }}>Send exactly {displayJob.payment_due} to the address above, then submit your payment proof below.</p>
            </div>
          )}

          {/* Payment proof submitted */}
          {displayJob.payment_proof && (
            <div style={{ backgroundColor: '#0a1a0a', border: `1px solid ${SUCCESS}33`, borderRadius: '8px', padding: '10px 12px', marginTop: '8px' }}>
              <p style={{ fontSize: '11px', color: SUCCESS, fontWeight: 600, marginBottom: '4px' }}>✅ Payment Proof Submitted by Client</p>
              <p style={{ fontSize: '12px', color: MUTED, wordBreak: 'break-all' }}>{displayJob.payment_proof}</p>
            </div>
          )}

          {/* Payment confirmed */}
          {displayJob.payment_confirmed === 'true' && (
            <div style={{ backgroundColor: '#051a0a', border: `1px solid ${SUCCESS}44`, borderRadius: '8px', padding: '10px 12px', marginTop: '8px', textAlign: 'center' }}>
              <p style={{ fontSize: '13px', color: SUCCESS, fontWeight: 700 }}>✓ Payment Confirmed — Job Complete</p>
              <p style={{ fontSize: '11px', color: MUTED, marginTop: '2px' }}>Both parties' reputation has been updated</p>
            </div>
          )}
        </div>
      )}

      {loadingPrivate && isParty && job._has_score === 'true' && (
        <div style={{ backgroundColor: '#0a0a14', border: `1px solid ${WARNING}33`, borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
          <p style={{ fontSize: '12px', color: MUTED }}>Loading score…</p>
        </div>
      )}

      {/* Mediation suggestion */}
      {displayJob.mediation_suggestion && isParty && (
        <div style={{ backgroundColor: '#14100a', border: `1px solid ${WARNING}33`, borderRadius: '8px', padding: '10px' }}>
          <p style={{ fontSize: '10px', color: WARNING, fontWeight: 600, marginBottom: '4px' }}>🤝 AI Mediation Suggestion</p>
          <p style={{ fontSize: '11px', color: MUTED, lineHeight: 1.5 }}>{displayJob.mediation_suggestion.slice(0, 200)}{displayJob.mediation_suggestion.length > 200 ? '…' : ''}</p>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '2px' }}>

        {/* Accept job */}
        {job.status === 'OPEN' && !isClient && (
          <button disabled={loading} onClick={() => onAction('accept_job', [job.job_id, address ?? ''])}
            style={{ backgroundColor: ORANGE, color: '#fff', border: 'none', borderRadius: '8px', padding: '10px', fontSize: '13px', fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.5 : 1 }}>
            Accept Job
          </button>
        )}

        {/* Cancel job */}
        {job.status === 'OPEN' && isClient && (
          <button disabled={loading} onClick={() => onAction('cancel_job', [job.job_id])}
            style={{ backgroundColor: 'transparent', color: MUTED, border: `1px solid ${BORDER}`, borderRadius: '8px', padding: '8px', fontSize: '12px', cursor: 'pointer' }}>
            Cancel Job
          </button>
        )}

        {/* Submit work */}
        {job.status === 'ACCEPTED' && isWorker && onOpenSubmit && (
          <button disabled={loading} onClick={() => onOpenSubmit(job.job_id, job.title, job.requirements)}
            style={{ backgroundColor: '#14102a', color: PURPLE, border: `1px solid ${PURPLE}44`, borderRadius: '8px', padding: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}>
            Submit Work → (AI will score automatically)
          </button>
        )}

        {/* Submit payment proof — client */}
        {job.status === 'SCORED' && isClient && displayJob.payment_pct !== '0' && !displayJob.payment_proof && (
          <>
            {!showPaymentProof ? (
              <button onClick={() => setShowPaymentProof(true)}
                style={{ backgroundColor: SUCCESS, color: '#fff', border: 'none', borderRadius: '8px', padding: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}>
                💸 Submit Payment Proof
              </button>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', backgroundColor: '#051a0a', border: `1px solid ${SUCCESS}33`, borderRadius: '8px', padding: '12px' }}>
                <p style={{ fontSize: '11px', color: SUCCESS, fontWeight: 600 }}>Submit proof that you sent {displayJob.payment_due} to {shortAddr(displayJob.worker_wallet)}:</p>
                <textarea value={paymentProof} onChange={e => setPaymentProof(e.target.value)}
                  placeholder="Paste your transaction hash, or describe the payment (e.g. 'Sent 50 GEN via MetaMask, tx hash: 0x123...')"
                  style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }} />
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button disabled={loading || !paymentProof.trim()} onClick={() => { onAction('submit_payment_proof', [job.job_id, paymentProof]); setShowPaymentProof(false); setPaymentProof('') }}
                    style={{ flex: 1, backgroundColor: SUCCESS, color: '#fff', border: 'none', borderRadius: '6px', padding: '10px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', opacity: paymentProof.trim() ? 1 : 0.5 }}>
                    Submit Proof
                  </button>
                  <button onClick={() => setShowPaymentProof(false)} style={{ backgroundColor: 'transparent', color: MUTED, border: `1px solid ${BORDER}`, borderRadius: '6px', padding: '10px', fontSize: '12px', cursor: 'pointer' }}>Cancel</button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Confirm payment received — worker */}
        {job.status === 'SCORED' && isWorker && displayJob.payment_pct !== '0' && displayJob.payment_proof && displayJob.payment_confirmed !== 'true' && (
          <button disabled={loading} onClick={() => onAction('confirm_payment_received', [job.job_id])}
            style={{ backgroundColor: SUCCESS, color: '#fff', border: 'none', borderRadius: '8px', padding: '10px', fontSize: '13px', fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.5 : 1 }}>
            ✓ Confirm Payment Received
          </button>
        )}

        {/* Flag payment default — worker */}
        {job.status === 'SCORED' && isWorker && displayJob.payment_pct !== '0' && displayJob.payment_confirmed !== 'true' && (
          <button disabled={loading} onClick={() => onAction('flag_payment_default', [job.job_id])}
            style={{ backgroundColor: 'transparent', color: DANGER, border: `1px solid ${DANGER}44`, borderRadius: '8px', padding: '8px', fontSize: '12px', cursor: 'pointer' }}>
            ⚠ Flag Payment Default
          </button>
        )}

        {/* Request mediation */}
        {job.status === 'SCORED' && isParty && !showMediation && (
          <button onClick={() => setShowMediation(true)}
            style={{ backgroundColor: 'transparent', color: WARNING, border: `1px solid ${WARNING}44`, borderRadius: '8px', padding: '8px', fontSize: '12px', cursor: 'pointer' }}>
            Request Mediation
          </button>
        )}
        {showMediation && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: '#14100a', border: `1px solid ${WARNING}33`, borderRadius: '8px', padding: '10px' }}>
            <textarea value={mediationPos} onChange={e => setMediationPos(e.target.value)} placeholder="Describe your position and what you believe is fair…" style={{ ...inputStyle, minHeight: '70px', resize: 'vertical' }} />
            <div style={{ display: 'flex', gap: '6px' }}>
              <button disabled={loading || !mediationPos.trim()} onClick={() => { onAction('request_mediation', [job.job_id, mediationPos]); setShowMediation(false); setMediationPos('') }}
                style={{ flex: 1, backgroundColor: WARNING, color: '#000', border: 'none', borderRadius: '6px', padding: '8px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', opacity: mediationPos.trim() ? 1 : 0.5 }}>
                Submit
              </button>
              <button onClick={() => setShowMediation(false)} style={{ backgroundColor: 'transparent', color: MUTED, border: `1px solid ${BORDER}`, borderRadius: '6px', padding: '8px', fontSize: '12px', cursor: 'pointer' }}>Cancel</button>
            </div>
          </div>
        )}

        {/* File dispute */}
        {job.status === 'SCORED' && isParty && !showDispute && (
          <button onClick={() => setShowDispute(true)}
            style={{ backgroundColor: 'transparent', color: DANGER, border: `1px solid ${DANGER}33`, borderRadius: '8px', padding: '8px', fontSize: '12px', cursor: 'pointer' }}>
            File Dispute
          </button>
        )}
        {showDispute && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: '#1a0505', border: `1px solid ${DANGER}33`, borderRadius: '8px', padding: '10px' }}>
            <p style={{ fontSize: '11px', color: DANGER, fontWeight: 500 }}>Explain why the AI score was incorrect:</p>
            <textarea value={disputeGrounds} onChange={e => setDisputeGrounds(e.target.value)} placeholder="What was wrong with the verdict? Provide specific evidence." style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }} />
            <div style={{ display: 'flex', gap: '6px' }}>
              <button disabled={loading || !disputeGrounds.trim()} onClick={() => { onAction('file_dispute', [job.job_id, disputeGrounds]); setShowDispute(false); setDisputeGrounds('') }}
                style={{ flex: 1, backgroundColor: DANGER, color: '#fff', border: 'none', borderRadius: '6px', padding: '8px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', opacity: disputeGrounds.trim() ? 1 : 0.5 }}>
                File Dispute
              </button>
              <button onClick={() => setShowDispute(false)} style={{ backgroundColor: 'transparent', color: MUTED, border: `1px solid ${BORDER}`, borderRadius: '6px', padding: '8px', fontSize: '12px', cursor: 'pointer' }}>Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function DisputeCard({ dispute, address, onAction, loading }: {
  dispute: Dispute; address?: string
  onAction: (m: string, a: unknown[]) => Promise<boolean>; loading: boolean
}) {
  const [showAppeal, setShowAppeal] = useState(false)
  const [appealGrounds, setAppealGrounds] = useState('')
  const finalPct = dispute.appeal_verdict_pct || dispute.verdict_pct
  const isParty = dispute.filer === address || dispute.defendant === address

  return (
    <div style={{ backgroundColor: CARD, border: `1px solid ${BORDER}`, borderRadius: '12px', padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
        <div>
          <p style={{ fontSize: '10px', color: MUTED, fontFamily: 'monospace' }}>Dispute #{dispute.dispute_id} · Job #{dispute.job_id}</p>
          <p style={{ fontWeight: 600, color: ORANGE, marginTop: '4px', fontSize: '15px' }}>{finalPct}% to worker</p>
        </div>
        <span style={{ fontSize: '10px', padding: '3px 8px', borderRadius: '20px', backgroundColor: dispute.status === 'FINAL' ? '#1a1a1a' : '#1a0505', color: dispute.status === 'FINAL' ? MUTED : DANGER, border: `1px solid ${dispute.status === 'FINAL' ? BORDER : DANGER + '44'}` }}>{dispute.status}</span>
      </div>
      {dispute.grounds && <p style={{ fontSize: '11px', color: MUTED, marginBottom: '8px' }}>Grounds: {dispute.grounds.slice(0, 120)}{dispute.grounds.length > 120 ? '…' : ''}</p>}
      {dispute.verdict_reasoning && <p style={{ fontSize: '12px', color: TEXT, lineHeight: 1.5, marginBottom: '8px' }}>{dispute.verdict_reasoning}</p>}
      {dispute.appeal_reasoning && (
        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: `1px solid ${BORDER}` }}>
          <p style={{ fontSize: '10px', color: ORANGE, fontWeight: 500, marginBottom: '4px' }}>Appeal Decision:</p>
          <p style={{ fontSize: '11px', color: MUTED, lineHeight: 1.5 }}>{dispute.appeal_reasoning}</p>
        </div>
      )}
      {dispute.status === 'RESOLVED' && isParty && (
        <div style={{ marginTop: '12px' }}>
          {!showAppeal ? (
            <button onClick={() => setShowAppeal(true)} style={{ backgroundColor: 'transparent', color: MUTED, border: `1px solid ${BORDER}`, borderRadius: '8px', padding: '8px 14px', fontSize: '12px', cursor: 'pointer' }}>Appeal Verdict</button>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <textarea value={appealGrounds} onChange={e => setAppealGrounds(e.target.value)} placeholder="Grounds for appeal — new evidence or clear error in reasoning…" style={{ ...inputStyle, minHeight: '70px', resize: 'vertical' }} />
              <div style={{ display: 'flex', gap: '6px' }}>
                <button disabled={loading || !appealGrounds.trim()} onClick={() => { onAction('appeal_verdict', [dispute.dispute_id, appealGrounds]); setShowAppeal(false); setAppealGrounds('') }}
                  style={{ flex: 1, backgroundColor: ORANGE, color: '#fff', border: 'none', borderRadius: '6px', padding: '8px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', opacity: appealGrounds.trim() ? 1 : 0.5 }}>
                  Submit Appeal
                </button>
                <button onClick={() => setShowAppeal(false)} style={{ backgroundColor: 'transparent', color: MUTED, border: `1px solid ${BORDER}`, borderRadius: '6px', padding: '8px', fontSize: '12px', cursor: 'pointer' }}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function CaseLawCard({ category, jobs, disputes }: { category: string; jobs: Job[]; disputes: Dispute[] }) {
  const catJobs = jobs.filter(j => j.category === category)
  const catDisputes = disputes.filter(d => d.category === category)
  const scores = catJobs.filter(j => j._has_score === 'true').map(j => parseInt(j.ai_score || '0')).filter(n => n > 0)
  const avgScore = scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null
  return (
    <div style={{ backgroundColor: CARD, border: `1px solid ${BORDER}`, borderRadius: '12px', padding: '16px' }}>
      <h4 style={{ fontWeight: 600, fontSize: '13px', marginBottom: '12px' }}>{category}</h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {[{ label: 'Jobs posted', value: catJobs.length, color: TEXT },
          { label: 'Scored', value: scores.length, color: WARNING },
          { label: 'Disputes', value: catDisputes.length, color: DANGER }].map(s => (
          <div key={s.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
            <span style={{ color: MUTED }}>{s.label}</span>
            <span style={{ color: s.color, fontWeight: 500 }}>{s.value}</span>
          </div>
        ))}
        {avgScore !== null && (
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
            <span style={{ color: MUTED }}>Avg AI score</span>
            <span style={{ color: scoreColor(avgScore), fontWeight: 600 }}>{avgScore}/100</span>
          </div>
        )}
        {catJobs.length === 0 && <p style={{ fontSize: '11px', color: MUTED }}>No cases yet</p>}
      </div>
    </div>
  )
}

function PostJobModal({ onClose, onSubmit, loading }: {
  onClose: () => void; onSubmit: (m: string, a: unknown[]) => Promise<boolean>; loading: boolean
}) {
  const [f, setF] = useState({ title: '', description: '', requirements: '', budget: '', category: SUPPORTED_CATEGORIES[0], milestone_count: '1' })
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setF(p => ({ ...p, [k]: e.target.value }))
  const canSubmit = f.title.trim() && f.description.trim() && f.requirements.trim() && f.budget.trim()

  return (
    <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.88)', zIndex: 150, display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }} onClick={onClose}>
      <div style={{ backgroundColor: '#0f0f0f', border: `1px solid ${BORDER}`, borderRadius: '16px 16px 0 0', padding: '24px 20px', width: '100%', maxWidth: '580px', maxHeight: '92vh', overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Post a Job</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: MUTED, fontSize: '22px', cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>
        <div style={{ backgroundColor: '#051a0a', border: `1px solid ${SUCCESS}33`, borderRadius: '8px', padding: '10px 12px', fontSize: '12px', color: SUCCESS, marginBottom: '16px', lineHeight: 1.5 }}>
          ℹ️ AI validators will score submitted work against your <strong>requirements</strong>. Be specific — vague requirements lead to unfair verdicts.
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div><label style={{ display: 'block', fontSize: '12px', color: MUTED, marginBottom: '5px' }}>Job Title *</label><input value={f.title} onChange={set('title')} placeholder="e.g. Write a 2000-word article about DeFi" style={inputStyle} /></div>
          <div><label style={{ display: 'block', fontSize: '12px', color: MUTED, marginBottom: '5px' }}>Description *</label><textarea value={f.description} onChange={set('description')} placeholder="Background, purpose, target audience…" style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }} /></div>
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: MUTED, marginBottom: '5px' }}>Acceptance Requirements * <span style={{ color: ORANGE }}>— AI judges against these</span></label>
            <textarea value={f.requirements} onChange={set('requirements')} placeholder={'List specific, measurable requirements:\n- Minimum 2000 words\n- Must cover: tokenomics, risks, use cases\n- Delivered as Google Doc\n- Original content'} style={{ ...inputStyle, minHeight: '110px', resize: 'vertical', fontFamily: 'monospace', fontSize: '12px' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div><label style={{ display: 'block', fontSize: '12px', color: MUTED, marginBottom: '5px' }}>Budget (GEN) *</label><input value={f.budget} onChange={set('budget')} placeholder="e.g. 500" style={inputStyle} /></div>
            <div><label style={{ display: 'block', fontSize: '12px', color: MUTED, marginBottom: '5px' }}>Category *</label><select value={f.category} onChange={set('category')} style={inputStyle}>{SUPPORTED_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}</select></div>
          </div>
          <div><label style={{ display: 'block', fontSize: '12px', color: MUTED, marginBottom: '5px' }}>Milestones</label><input type="number" min="1" max="10" value={f.milestone_count} onChange={set('milestone_count')} style={inputStyle} /></div>
          <button disabled={loading || !canSubmit} onClick={() => { onSubmit('create_job', [f.title, f.description, f.requirements, f.budget, f.category, f.milestone_count]); onClose() }}
            style={{ backgroundColor: ORANGE, color: '#fff', border: 'none', borderRadius: '10px', padding: '14px', fontSize: '15px', fontWeight: 600, cursor: canSubmit ? 'pointer' : 'not-allowed', opacity: canSubmit ? 1 : 0.5 }}>
            Post Job
          </button>
        </div>
      </div>
    </div>
  )
}

function SubmitWorkModal({ job, onClose, onSubmit, loading }: {
  job: { jobId: string; title: string; requirements: string }
  onClose: () => void; onSubmit: (m: string, a: unknown[]) => Promise<boolean>; loading: boolean
}) {
  const [link, setLink] = useState('')
  const [desc, setDesc] = useState('')
  const canSubmit = link.trim() && desc.trim()

  return (
    <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.88)', zIndex: 150, display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }} onClick={onClose}>
      <div style={{ backgroundColor: '#0f0f0f', border: `1px solid ${BORDER}`, borderRadius: '16px 16px 0 0', padding: '24px 20px', width: '100%', maxWidth: '580px', maxHeight: '92vh', overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Submit Work</h2>
            <p style={{ fontSize: '12px', color: MUTED, marginTop: '2px' }}>Job #{job.jobId}: {job.title}</p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: MUTED, fontSize: '22px', cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>
        {job.requirements && (
          <div style={{ backgroundColor: '#0a0a1a', border: `1px solid ${PURPLE}33`, borderRadius: '8px', padding: '10px 12px', fontSize: '11px', color: MUTED, marginBottom: '12px', fontFamily: 'monospace', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            <p style={{ color: PURPLE, fontWeight: 600, marginBottom: '6px', fontFamily: 'inherit' }}>Requirements to meet:</p>
            {job.requirements}
          </div>
        )}
        <div style={{ backgroundColor: '#0a0a14', border: `1px solid ${PURPLE}33`, borderRadius: '8px', padding: '10px 12px', fontSize: '12px', color: PURPLE, marginBottom: '16px', lineHeight: 1.5 }}>
          ⚡ AI validators will automatically score your submission. This takes 1–3 minutes after you submit.
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div><label style={{ display: 'block', fontSize: '12px', color: MUTED, marginBottom: '5px' }}>Deliverable Link *</label><input value={link} onChange={e => setLink(e.target.value)} placeholder="GitHub repo, Google Doc, deployed URL, etc." style={inputStyle} /></div>
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: MUTED, marginBottom: '5px' }}>How did you meet the requirements? * <span style={{ color: PURPLE }}>— AI reads this</span></label>
            <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="Go through each requirement and explain exactly how your submission meets it. The more specific, the better your score." style={{ ...inputStyle, minHeight: '130px', resize: 'vertical' }} />
          </div>
          <button disabled={loading || !canSubmit} onClick={() => { onSubmit('submit_work', [job.jobId, link, desc]); onClose() }}
            style={{ backgroundColor: PURPLE, color: '#fff', border: 'none', borderRadius: '10px', padding: '14px', fontSize: '15px', fontWeight: 600, cursor: canSubmit ? 'pointer' : 'not-allowed', opacity: canSubmit ? 1 : 0.5 }}>
            Submit Work (AI Scores Automatically)
          </button>
        </div>
      </div>
    </div>
  )
}
