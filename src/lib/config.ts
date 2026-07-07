export const CONTRACT_ADDRESS = '0x09c460AB5f8A4Dd110e9417de4842Ec469D1092b' as `0x${string}`

export const BRADBURY_CHAIN = {
  id: 4221,
  name: 'GenLayer Bradbury Testnet',
  nativeCurrency: { decimals: 18, name: 'GEN', symbol: 'GEN' },
  rpcUrls: { default: { http: ['https://rpc-bradbury.genlayer.com'] } },
  blockExplorers: { default: { name: 'Bradbury Explorer', url: 'https://explorer-bradbury.genlayer.com' } },
  testnet: true,
} as const

export const TX_POLL_INTERVAL_MS = 3000
export const TX_TIMEOUT_MS = 15 * 60 * 1000

export const JOB_STATUS_LABELS: Record<string, string> = {
  OPEN: 'Open',
  ACCEPTED: 'In Progress',
  SUBMITTED: 'Work Submitted',
  COMPLETED: 'Completed',
  DISPUTED: 'Disputed',
  RESOLVED: 'Resolved',
  CANCELLED: 'Cancelled',
}

export const VERDICT_LABELS: Record<string, string> = {
  '0': 'Full Refund to Client',
  '25': 'Mostly Client Wins',
  '50': 'Split Decision',
  '75': 'Mostly Worker Wins',
  '100': 'Full Payment to Worker',
}
