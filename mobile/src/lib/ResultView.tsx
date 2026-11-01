import { StyleSheet, Text, View } from 'react-native'
import { colors } from './theme'
import type { Diagnosis } from './types'
import { worstRisk } from './util'
import { Banner, Card, Chip, RiskBadge, SectionTitle } from './ui'

const LABEL = { most_likely: 'Most likely', possible: 'Possible' } as const

export function ResultView({ diagnosis }: { diagnosis: Diagnosis }) {
  if (diagnosis.status === 'unsupported') {
    return (
      <Card>
        <SectionTitle>Not recognised</SectionTitle>
        <Text style={s.body}>
          {diagnosis.notice ?? "This doesn't look like one of the supported appliances."}
        </Text>
      </Card>
    )
  }

  const plan = diagnosis.plan
  const worst = worstRisk(plan)
  const stopped = worst === 'stop'

  return (
    <View style={{ gap: 16 }}>
      <Card>
        <Text style={s.caption}>Appliance</Text>
        <Text style={s.title}>{diagnosis.appliance ?? 'Unknown appliance'}</Text>
        {worst ? <RiskBadge risk={worst} prefix='Overall: ' /> : null}
      </Card>

      {stopped ? (
        <Banner
          tone='critical'
          title="Stop: don't use or repair this appliance"
          text='This looks like a safety risk. Follow the steps below and contact a qualified technician.'
        />
      ) : plan?.escalate ? (
        <Banner
          tone='warning'
          title='A professional is recommended'
          text='The safe checks below may not be enough to fix this.'
        />
      ) : null}

      {diagnosis.notice ? (
        <Card>
          <Text style={s.body}>{diagnosis.notice}</Text>
        </Card>
      ) : null}

      {diagnosis.hypotheses.length > 0 ? (
        <Card>
          <SectionTitle>Possible causes</SectionTitle>
          {diagnosis.hypotheses.map((h) => (
            <View key={h.fault_id} style={s.hypRow}>
              <Chip text={LABEL[h.label]} tone={h.label === 'most_likely' ? 'accent' : 'muted'} />
              <Text style={[s.body, { flex: 1 }]}>{h.name}</Text>
            </View>
          ))}
          <Text style={s.caption}>
            Based on your photo and answers. These are possibilities, not a confirmed diagnosis.
          </Text>
        </Card>
      ) : null}

      {diagnosis.observation.visible_issues.length > 0 ? (
        <Card>
          <SectionTitle>What we noticed in the photo</SectionTitle>
          <View style={s.wrap}>
            {diagnosis.observation.visible_issues.map((v) => (
              <Chip key={v} text={v} />
            ))}
          </View>
        </Card>
      ) : null}

      {plan ? (
        <View style={{ gap: 12 }}>
          <SectionTitle>What to do</SectionTitle>
          {plan.summary ? <Text style={s.body}>{plan.summary}</Text> : null}
          {plan.steps.map((step) => (
            <Card key={step.order}>
              <View style={s.stepHead}>
                <View style={s.num}>
                  <Text style={s.numText}>{step.order}</Text>
                </View>
                <RiskBadge risk={step.risk} />
              </View>
              <Text style={s.body}>{step.instruction}</Text>
              {step.stop_if ? <Text style={s.stopIf}>Stop if: {step.stop_if}</Text> : null}
            </Card>
          ))}
        </View>
      ) : null}

      <Text style={s.caption}>
        Never open the casing or touch internal electrical parts. If you notice a burning smell,
        sparks or unusual heat, stop using the appliance.
      </Text>
    </View>
  )
}

const s = StyleSheet.create({
  caption: { color: colors.textMuted, fontSize: 13, lineHeight: 18 },
  title: { color: colors.text, fontSize: 24, fontWeight: '800' },
  body: { color: colors.text, fontSize: 15, lineHeight: 22 },
  hypRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  stepHead: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  num: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  numText: { color: colors.onAccent, fontWeight: '800' },
  stopIf: { color: colors.warning, fontSize: 14, fontWeight: '600' },
})
