export type Risk = 'low' | 'medium' | 'high' | 'stop'
export type Status = 'needs_answers' | 'complete' | 'unsupported'

export interface Question {
  id: string
  text: string
  options: string[]
}
export interface Step {
  order: number
  instruction: string
  risk: Risk
  stop_if: string | null
}
export interface Plan {
  summary: string
  escalate: boolean
  steps: Step[]
}
export interface Hypothesis {
  fault_id: string
  name: string
  label: 'most_likely' | 'possible'
}
export interface Observation {
  object_id: string
  components: string[]
  visible_issues: string[]
  note?: string
}

export interface Diagnosis {
  id: string
  status: Status
  appliance: string | null
  observation: Observation
  questions: Question[]
  hypotheses: Hypothesis[]
  plan: Plan | null
  notice: string | null
}

export interface Supported {
  id: string
  name: string
}
