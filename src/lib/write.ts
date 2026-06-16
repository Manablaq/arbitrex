'use client'
import { writeContractWithWallet, type TxResult } from './genlayer'

export async function callWrite(
  address: string | undefined,
  method: string,
  args: unknown[],
  setStatus: (s: string | null) => void,
  setError: (s: string | null) => void,
  setLoading: (b: boolean) => void
): Promise<boolean> {
  if (!address) {
    setError('Connect your wallet first.')
    return false
  }
  setLoading(true)
  setStatus(`Submitting ${method}… (AI validators may take 1-3 minutes)`)
  setError(null)
  try {
    const result: TxResult = await writeContractWithWallet(address, method, args)
    if (result.success) {
      setStatus(`✓ Success! Tx: ${result.txHash?.slice(0, 20)}…`)
      setLoading(false)
      return true
    } else {
      setError(`Transaction failed: ${result.error}`)
      setLoading(false)
      return false
    }
  } catch (e: any) {
    setError(e?.message ?? String(e))
    setLoading(false)
    return false
  }
}
