import { WorkflowEntrypoint } from 'cloudflare:workers'
import Mustache from 'mustache'

import digestTpl from '../templates/digest.mustache'

const BATCH_SIZE = 50
const LIST_UNSUBSCRIBE = '<mailto:unsubscribe@paper-picnic.com?subject=unsubscribe&body=unsubscribe>'

// --- Plunk ---

async function sendPlunkEmail(to, subject, body, env, { reply, headers } = {}) {
  const resp = await fetch('https://next-api.useplunk.com/v1/send', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.PLUNK_SECRET_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      to,
      from: 'noreply@paper-picnic.com',
      subject,
      body,
      subscribed: false,
      ...(reply && { reply }),
      ...(headers && { headers }),
    }),
  })
  if (!resp.ok) console.error('Plunk error:', resp.status, await resp.text())
  return resp.ok
}

// --- Content builders ---

function formatDate(dateString) {
  return new Date(dateString + 'T12:00:00Z').toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  })
}

function buildJournalMap(journalsData) {
  return Object.fromEntries(journalsData.map(j => [j.id, { category: j.category, category_rank: j.category_rank, name: j.name }]))
}

function buildSubgroupMap(osfSubjects) {
  return Object.fromEntries((osfSubjects.subgroups || []).map(sg => [sg.id, sg.name]))
}

function buildOsfIdToSubgroup(osfSubjects) {
  const map = {}
  for (const sg of osfSubjects.subgroups || []) {
    for (const osf of sg.osf || []) {
      map[osf.id] = sg.id
    }
  }
  return map
}

function groupBySubscriber(rows, valueKey) {
  const map = {}
  for (const row of rows) {
    if (!map[row.subscriber_id]) map[row.subscriber_id] = []
    map[row.subscriber_id].push(row[valueKey])
  }
  return map
}

function buildDisciplineSections(pubContent, journalMap, subscriberJournalIds) {
  const selected = new Set(subscriberJournalIds)
  const byCategory = {}
  for (const pub of pubContent) {
    const info = journalMap[pub.journal_id]
    if (!info || !selected.has(pub.journal_id)) continue
    if (!pub.articles || pub.articles.length === 0) continue
    if (!byCategory[info.category]) {
      byCategory[info.category] = { rank: info.category_rank, journals: [] }
    }
    byCategory[info.category].journals.push({
      journal_name: pub.journal_name,
      rank: info.category_rank,
      articles: pub.articles,
    })
  }
  return Object.entries(byCategory)
    .sort((a, b) => a[1].rank - b[1].rank)
    .map(([name, data]) => ({
      id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      name,
      journals: data.journals.sort((a, b) => a.rank - b.rank),
    }))
}

function buildPreprintsSection(preprints, osfIdToSubgroup, subgroupMap, subscriberOsfCategories) {
  const articles = preprints?.content?.articles
  if (!articles || subscriberOsfCategories.length === 0) return null
  const selected = new Set(subscriberOsfCategories)
  const bySubgroup = {}
  for (const article of articles) {
    const subgroupIds = new Set((article.subjects || []).map(s => osfIdToSubgroup[s.id]).filter(Boolean))
    for (const sgId of subgroupIds) {
      if (!selected.has(sgId)) continue
      if (!bySubgroup[sgId]) bySubgroup[sgId] = []
      bySubgroup[sgId].push(article)
    }
  }
  const groups = Object.entries(bySubgroup).map(([id, items]) => ({ group_name: subgroupMap[id] || id, items }))
  return groups.length > 0 ? { groups } : null
}

// --- Workflow ---

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
        const subject = `[Paper Picnic] New Baskets from ${formatDate(issueKey)}`

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
