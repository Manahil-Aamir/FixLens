import type { Plan, Risk } from './types'

const ORDER: Risk[] = ['low', 'medium', 'high', 'stop']

export function worstRisk(plan: Plan | null): Risk | null {
  if (!plan || plan.steps.length === 0) return null
  return plan.steps.reduce<Risk>(
    (worst, s) => (ORDER.indexOf(s.risk) > ORDER.indexOf(worst) ? s.risk : worst),
    'low',
  )
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}
