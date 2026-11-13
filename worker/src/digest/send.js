// Queue consumer: renders and sends the digest for each subscriber in a batch,
// then marks them as sent. A batch is at most 5 messages (wrangler.toml), so one
// invocation makes at most 5 Plunk requests.

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

const LIST_UNSUBSCRIBE = '<mailto:unsubscribe@paper-picnic.com?subject=unsubscribe&body=unsubscribe>'

export async function sendDigestBatch(batch, env) {
  const [publications, preprints, journalsData, osfSubjects] = await Promise.all([
    env.KV.get('publications', 'json'),
    env.KV.get('preprints', 'json'),
    env.KV.get('journals', 'json'),
    env.KV.get('osf_subjects', 'json'),
  ])

  const ids = batch.messages.map(m => m.body.subscriberId)
  const placeholders = ids.map(() => '?').join(',')
  const [subs, journalPrefs, osfPrefs] = await env.DB.batch([
    env.DB.prepare(`SELECT id, email, last_sent_week FROM subscribers WHERE id IN (${placeholders})`).bind(...ids),
    env.DB.prepare(`SELECT subscriber_id, journal_id FROM journal_preferences WHERE subscriber_id IN (${placeholders})`).bind(...ids),
    env.DB.prepare(`SELECT subscriber_id, osf_category FROM preprint_preferences WHERE subscriber_id IN (${placeholders})`).bind(...ids),
  ])

  const subsById = new Map(subs.results.map(s => [s.id, s]))
  const journalsBySub = groupBySubscriber(journalPrefs.results, 'journal_id')
  const osfBySub = groupBySubscriber(osfPrefs.results, 'osf_category')
  const journalMap = buildJournalMap(journalsData)
  const subgroupMap = buildSubgroupMap(osfSubjects)
  const osfIdToSubgroup = buildOsfIdToSubgroup(osfSubjects)

  for (const msg of batch.messages) {
    const { subscriberId, issueKey } = msg.body

    // KV not yet showing this issue: try again later. A newer issue: drop the message.
    if (publications?.update !== issueKey) {
      if (!publications?.update || publications.update < issueKey) msg.retry({ delaySeconds: 60 })
      else msg.ack()
      continue
    }

    // Unsubscribed or already sent.
    const sub = subsById.get(subscriberId)
    if (!sub || sub.last_sent_week === issueKey) {
      msg.ack()
      continue
    }

    // An empty selection still gets an email, saying there are no new papers.
    const disciplines = buildDisciplineSections(publications.content, journalMap, journalsBySub[sub.id] || [])
    const preprintsContent = buildPreprintsSection(preprints, osfIdToSubgroup, subgroupMap, osfBySub[sub.id] || [])
    const empty = disciplines.length === 0 && !preprintsContent

    const html = Mustache.render(digestTpl, { disciplines, preprints: preprintsContent, empty })
    const sent = await sendPlunkEmail(sub.email, `[Paper Picnic] Melting Pot from ${formatDate(issueKey)}`, html, env, {
      reply: 'hello@paper-picnic.com',
      headers: { 'List-Unsubscribe': LIST_UNSUBSCRIBE },
      subscriberId: sub.id,
    })
    if (!sent) {
      msg.retry({ delaySeconds: 60 })
      continue
    }

    await env.DB.prepare('UPDATE subscribers SET last_sent_week = ? WHERE id = ?').bind(issueKey, sub.id).run()
    msg.ack()
  }
}
