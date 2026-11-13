import { WorkflowEntrypoint } from 'cloudflare:workers'
import Mustache from 'mustache'

import { sendPlunkEmail } from '../lib/plunk.js'
import {
  buildDisciplineSections,
  buildJournalMap,
  buildOsfIdToSubgroup,
  buildPreprintsSection,
  buildSubgroupMap,
  formatDate,
  groupBySubscriber,
} from './build.js'

import digestTpl from '../../templates/digest/digest.mustache'

const BATCH_SIZE = 5
const LIST_UNSUBSCRIBE = '<mailto:unsubscribe@paper-picnic.com?subject=unsubscribe&body=unsubscribe>'

export class WeeklyDigestWorkflow extends WorkflowEntrypoint {
  async run(event, step) {
    const { issueKey, subscribers } = await step.do('fetch-subscribers', async () => {
      const publications = await this.env.KV.get('publications', 'json')
      if (!publications?.update || !publications?.content) return { issueKey: null, subscribers: [] }

      const today = new Date().toISOString().slice(0, 10)
      if (!event.payload?.skipDateCheck && publications.update !== today) {
        console.log(`Skipping: publications.json is for ${publications.update}, not ${today}`)
        return { issueKey: null, subscribers: [] }
      }

      const { results } = await this.env.DB.prepare(
        'SELECT id, email FROM subscribers WHERE last_sent_week IS NULL OR last_sent_week != ?'
      ).bind(publications.update).all()

      return { issueKey: publications.update, subscribers: results }
    })

    if (!issueKey || subscribers.length === 0) return

    const batches = []
    for (let i = 0; i < subscribers.length; i += BATCH_SIZE) {
      batches.push(subscribers.slice(i, i + BATCH_SIZE))
    }

    for (const [i, batch] of batches.entries()) {
      await step.do(`send-batch-${i}`, async () => {
        const [publications, preprints, journalsData, osfSubjects] = await Promise.all([
          this.env.KV.get('publications', 'json'),
          this.env.KV.get('preprints', 'json'),
          this.env.KV.get('journals', 'json'),
          this.env.KV.get('osf_subjects', 'json'),
        ])
        if (!publications?.content) return

        const journalMap = buildJournalMap(journalsData)
        const subgroupMap = buildSubgroupMap(osfSubjects)
        const osfIdToSubgroup = buildOsfIdToSubgroup(osfSubjects)
        const subject = `[Paper Picnic] Melting Pot from ${formatDate(issueKey)}`

        const ids = batch.map(s => s.id)
        const placeholders = ids.map(() => '?').join(',')

        // Fetch preferences and already-sent status in one round-trip
        const [journalPrefs, osfPrefs, sentRows] = await this.env.DB.batch([
          this.env.DB.prepare(`SELECT subscriber_id, journal_id FROM journal_preferences WHERE subscriber_id IN (${placeholders})`).bind(...ids),
          this.env.DB.prepare(`SELECT subscriber_id, osf_category FROM preprint_preferences WHERE subscriber_id IN (${placeholders})`).bind(...ids),
          this.env.DB.prepare(`SELECT id FROM subscribers WHERE id IN (${placeholders}) AND last_sent_week = ?`).bind(...ids, issueKey),
        ])

        const journalsBySub = groupBySubscriber(journalPrefs.results, 'journal_id')
        const osfBySub = groupBySubscriber(osfPrefs.results, 'osf_category')
        const alreadySent = new Set(sentRows.results.map(r => r.id))

        for (const sub of batch) {
          if (alreadySent.has(sub.id)) continue

          const disciplines = buildDisciplineSections(publications.content, journalMap, journalsBySub[sub.id] || [])
          const preprintsContent = buildPreprintsSection(preprints, osfIdToSubgroup, subgroupMap, osfBySub[sub.id] || [])
          if (disciplines.length === 0 && !preprintsContent) continue

          const html = Mustache.render(digestTpl, { disciplines, preprints: preprintsContent })
          const sent = await sendPlunkEmail(sub.email, subject, html, this.env, {
            reply: 'hello@paper-picnic.com',
            headers: { 'List-Unsubscribe': LIST_UNSUBSCRIBE },
            subscriberId: sub.id,
          })
          if (sent) {
            await this.env.DB.prepare(
              'UPDATE subscribers SET last_sent_week = ? WHERE id = ?'
            ).bind(issueKey, sub.id).run()
          }
        }
      })
    }
  }
}
