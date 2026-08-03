import { EmailMessage } from 'cloudflare:email'
import Mustache from 'mustache'
import PostalMime from 'postal-mime'
import { createMimeMessage } from 'mimetext'

import { extractBlock, parseSelections, stripTags } from './parse.js'
import { UNIVERSITY_DOMAINS } from './university-domains.js'

import digestTpl from '../templates/digest.mustache'
import replySubscribedTpl from '../templates/reply-subscribed.mustache'
import replyUnsubscribedTpl from '../templates/reply-unsubscribed.mustache'
import replyHelpTpl from '../templates/reply-help.mustache'
import replyNonUniversityTpl from '../templates/reply-nonuniversity.mustache'

const BATCH_SIZE = 10

// The Worker only acts on mail delivered to these two addresses; anything else
// is ignored (the catch-all route sends other mail to a human inbox).
const SUBSCRIBE_ADDRESS = 'subscribe@paper-picnic.com'
const UNSUBSCRIBE_ADDRESS = 'unsubscribe@paper-picnic.com'

const PUBLICATIONS_URL = 'https://raw.githubusercontent.com/sumtxt/picnic/main/output/publications.json'
const PREPRINTS_URL = 'https://raw.githubusercontent.com/sumtxt/picnic/main/output/preprints.json'
const JOURNALS_URL = 'https://raw.githubusercontent.com/sumtxt/picnic/main/parameters/journals.json'
const OSF_SUBJECTS_URL = 'https://raw.githubusercontent.com/sumtxt/picnic/main/parameters/osf_subjects.json'

// --- Helpers ---

// Sign-ups are limited to institutional addresses (bundled Hipo university-domains list).
function isUniversityEmail(email) {
  const parts = email.toLowerCase().split('@')
  if (parts.length !== 2) return false
  return UNIVERSITY_DOMAINS.has(parts[1])
}

async function sendPlunkEmail(to, subject, body, env, { reply, headers } = {}) {
  const payload = {
    to,
    from: 'noreply@paper-picnic.com',
    subject,
    body,
    subscribed: false,
  }
  if (reply) payload.reply = reply
  if (headers) payload.headers = headers

  const resp = await fetch('https://next-api.useplunk.com/v1/send', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.PLUNK_SECRET_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  if (!resp.ok) {
    const text = await resp.text()
    console.error('Plunk error:', resp.status, text)
  }
  return resp.ok
}

// --- Weekly send (cron) ---

function formatDate(dateString) {
  return new Date(dateString + 'T12:00:00Z').toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  })
}

function buildJournalMap(journalsData) {
  const map = {}
  for (const j of journalsData) {
    map[j.id] = { category: j.category, category_rank: j.category_rank, name: j.name }
  }
  return map
}

function buildSubgroupMap(osfSubjects) {
  const map = {}
  for (const sg of (osfSubjects.subgroups || [])) {
    map[sg.id] = sg.name
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
    .map(([name, data]) => {
      const journals = data.journals.sort((a, b) => a.rank - b.rank)
      return {
        id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
        name,
        journals,
      }
    })
}

function buildPreprintsSection(preprints, subgroupMap, subscriberOsfCategories) {
  if (!preprints || !preprints.content || subscriberOsfCategories.length === 0) return null
  const selected = new Set(subscriberOsfCategories)
  const groups = []
  for (const group of preprints.content) {
    if (!selected.has(group.id)) continue
    if (!group.items || group.items.length === 0) continue
    groups.push({ group_name: subgroupMap[group.id] || group.id, items: group.items })
  }
  if (groups.length === 0) return null
  return { groups }
}

async function runWeeklySend(env) {
  // Quick pre-check using only D1: any subscriber that hasn't received something in 6+ days?
  const staleRow = await env.DB.prepare(
    "SELECT COUNT(*) as cnt FROM subscribers WHERE (last_sent_week IS NULL OR last_sent_week < date('now', '-6 days'))"
  ).first()
  if (!staleRow || staleRow.cnt === 0) return

  // Fetch current publications to determine the issue key
  const pubResp = await fetch(PUBLICATIONS_URL)
  if (!pubResp.ok) return
  const publications = await pubResp.json()
  const issueKey = publications.update
  if (!issueKey || !publications.content) return

  // Get a batch of subscribers not yet sent this issue
  const pending = await env.DB.prepare(
    'SELECT id, email FROM subscribers WHERE (last_sent_week IS NULL OR last_sent_week != ?) LIMIT ?'
  ).bind(issueKey, BATCH_SIZE).all()
  if (pending.results.length === 0) return

  // Fetch supporting data in parallel
  const [prepResp, journalsResp, osfResp] = await Promise.all([
    fetch(PREPRINTS_URL),
    fetch(JOURNALS_URL),
    fetch(OSF_SUBJECTS_URL),
  ])
  const preprints = prepResp.ok ? await prepResp.json() : null
  const journalsData = journalsResp.ok ? await journalsResp.json() : []
  const osfSubjects = osfResp.ok ? await osfResp.json() : { subgroups: [] }

  const journalMap = buildJournalMap(journalsData)
  const subgroupMap = buildSubgroupMap(osfSubjects)
  const formattedDate = formatDate(issueKey)
  const subject = `[Paper Picnic] New Baskets from ${formattedDate}`

  // Fetch all preferences for this batch in one round-trip
  const ids = pending.results.map(s => s.id)
  const placeholders = ids.map(() => '?').join(',')
  const [journalPrefs, osfPrefs] = await env.DB.batch([
    env.DB.prepare(`SELECT subscriber_id, journal_id FROM journal_preferences WHERE subscriber_id IN (${placeholders})`).bind(...ids),
    env.DB.prepare(`SELECT subscriber_id, osf_category FROM preprint_preferences WHERE subscriber_id IN (${placeholders})`).bind(...ids),
  ])

  const journalsBySub = {}
  for (const row of journalPrefs.results) {
    if (!journalsBySub[row.subscriber_id]) journalsBySub[row.subscriber_id] = []
    journalsBySub[row.subscriber_id].push(row.journal_id)
  }
  const osfBySub = {}
  for (const row of osfPrefs.results) {
    if (!osfBySub[row.subscriber_id]) osfBySub[row.subscriber_id] = []
    osfBySub[row.subscriber_id].push(row.osf_category)
  }

  const listUnsubscribeHeader = '<mailto:unsubscribe@paper-picnic.com?subject=unsubscribe&body=unsubscribe>'

  // Send emails sequentially (respects the 6-simultaneous-connections limit)
  for (const sub of pending.results) {
    const disciplines = buildDisciplineSections(
      publications.content, journalMap, journalsBySub[sub.id] || []
    )
    const preprintsContent = buildPreprintsSection(
      preprints, subgroupMap, osfBySub[sub.id] || []
    )
    if (disciplines.length > 0 || preprintsContent) {
      const html = Mustache.render(digestTpl, {
        disciplines,
        preprints: preprintsContent,
      })
      await sendPlunkEmail(sub.email, subject, html, env, {
        // Replies go to a human; one-click unsubscribe stays on the header below.
        reply: 'hello@paper-picnic.com',
        headers: {
          'List-Unsubscribe': listUnsubscribeHeader,
        },
      })
    }
  }

  // Mark this entire batch as sent for this issue
  await env.DB.batch(
    ids.map(id =>
      env.DB.prepare('UPDATE subscribers SET last_sent_week = ? WHERE id = ?').bind(issueKey, id)
    )
  )
}

// --- Email handler ---

/**
 * Build a MIME reply body and call message.reply().
 * Uses mimetext to construct a plain-text MIME message.
 */
async function sendReply(message, subject, body) {
  const msg = createMimeMessage()
  // Threading: Cloudflare requires In-Reply-To referencing the incoming Message-ID.
  const messageId = message.headers.get('Message-ID')
  if (messageId) {
    msg.setHeader('In-Reply-To', messageId)
    msg.setHeader('References', messageId)
  }
  // Sender must be on the same domain that received the mail; use the exact To address.
  msg.setSender({ name: 'Paper Picnic', addr: message.to })
  msg.setRecipient(message.from)
  msg.setSubject(subject)
  msg.addMessage({ contentType: 'text/plain', data: body })

  await message.reply(new EmailMessage(message.to, message.from, msg.asRaw()))
}

/**
 * Upsert a subscriber by email, replacing all preferences.
 */
async function upsertSubscriber(email, journals, osf, env) {
  const existing = await env.DB.prepare(
    'SELECT id FROM subscribers WHERE email = ?'
  ).bind(email).first()

  const id = existing ? existing.id : crypto.randomUUID()
  const now = new Date().toISOString()

  const stmts = []

  if (existing) {
    // Replace preferences
    stmts.push(
      env.DB.prepare('DELETE FROM journal_preferences WHERE subscriber_id = ?').bind(id),
      env.DB.prepare('DELETE FROM preprint_preferences WHERE subscriber_id = ?').bind(id),
    )
  } else {
    stmts.push(
      env.DB.prepare('INSERT INTO subscribers (id, email, created_at) VALUES (?, ?, ?)').bind(id, email, now),
    )
  }

  for (const jid of journals) {
    stmts.push(env.DB.prepare('INSERT INTO journal_preferences (subscriber_id, journal_id) VALUES (?, ?)').bind(id, jid))
  }
  for (const cat of osf) {
    stmts.push(env.DB.prepare('INSERT INTO preprint_preferences (subscriber_id, osf_category) VALUES (?, ?)').bind(id, cat))
  }

  await env.DB.batch(stmts)
}

/**
 * Delete a subscriber by email, removing their preference rows explicitly
 * (does not rely on ON DELETE CASCADE, which is a no-op if D1 FK enforcement
 * is off — that would otherwise leave orphaned preference rows).
 */
async function deleteSubscriber(email, env) {
  const sub = await env.DB.prepare(
    'SELECT id FROM subscribers WHERE email = ?'
  ).bind(email).first()
  if (!sub) return false

  await env.DB.batch([
    env.DB.prepare('DELETE FROM journal_preferences WHERE subscriber_id = ?').bind(sub.id),
    env.DB.prepare('DELETE FROM preprint_preferences WHERE subscriber_id = ?').bind(sub.id),
    env.DB.prepare('DELETE FROM subscribers WHERE id = ?').bind(sub.id),
  ])
  return true
}

/**
 * Inbound email handler.
 * Called by Cloudflare Email Routing when an email arrives at the Worker.
 */
async function handleEmail(message, env) {
  // 1. Parse the MIME message (safe to do before auth — it's just parsing)
  const parser = new PostalMime()
  const email = await parser.parse(message.raw)

  // 2. DMARC check. Use the TOPMOST Authentication-Results header — the one
  // prepended by Cloudflare (the receiving MTA). A sender can forge their own
  // AR header, but it sits below Cloudflare's, so checking headers.get() (which
  // concatenates all of them) would be spoofable. `\bdmarc=pass\b` avoids
  // matching values like `dmarc=passfail`. (Pinning Cloudflare's authserv-id
  // would be even stricter.)
  const arHeaders = email.headers.filter(h => (h.key || '').toLowerCase() === 'authentication-results')
  const receiverAr = arHeaders.length ? arHeaders[0].value : ''
  if (!/\bdmarc=pass\b/i.test(receiverAr)) {
    message.setReject('Could not verify sender domain (DMARC).')
    return
  }

  // Identity = DMARC-verified envelope From; intent = the address it was sent to.
  const from = (message.from || '').trim().toLowerCase()
  const to = (message.to || '').trim().toLowerCase()

  // 3. Unsubscribe: any mail delivered to the unsubscribe address. The content
  // is irrelevant, so a one-click List-Unsubscribe, a plain email, or a reply
  // all work — nothing else reaches this address (digest Reply-To is hello@).
  if (to === UNSUBSCRIBE_ADDRESS) {
    await deleteSubscriber(from, env)
    const body = Mustache.render(replyUnsubscribedTpl, {})
    await sendReply(message, 'Re: Unsubscribed from Paper Picnic', body)
    return
  }

  // 4. Only subscribe@ is handled beyond this point. Ignore anything else so a
  // routing change can't make the Worker treat arbitrary mail as a subscription.
  if (to !== SUBSCRIBE_ADDRESS) return

  // 5. Subscribe: parse the #PICNIC block (prefer text/plain; fall back to
  //    tag-stripped HTML).
  const bodyText = email.text || (email.html ? stripTags(email.html) : '')
  const block = extractBlock(bodyText)
  if (block) {
    // Whitelist the selections against the known journal / OSF ids.
    const [journalsResp, osfResp] = await Promise.all([
      fetch(JOURNALS_URL),
      fetch(OSF_SUBJECTS_URL),
    ])
    const journalsData = journalsResp.ok ? await journalsResp.json() : []
    const osfSubjectsData = osfResp.ok ? await osfResp.json() : { subgroups: [] }

    const journalIds = new Set(journalsData.map(j => j.id))
    const osfIds = new Set((osfSubjectsData.subgroups || []).map(sg => sg.id))

    const selections = parseSelections(block, { journalIds, osfIds })

    // Need at least one valid id, and a university/institutional address.
    if (selections.journals.length > 0 || selections.osf.length > 0) {
      if (!isUniversityEmail(from)) {
        const body = Mustache.render(replyNonUniversityTpl, {})
        await sendReply(message, 'Re: Paper Picnic subscription', body)
        return
      }
      await upsertSubscriber(from, selections.journals, selections.osf, env)
      const body = Mustache.render(replySubscribedTpl, {})
      await sendReply(message, 'Re: Subscribed to Paper Picnic', body)
      return
    }
  }

  // 6. Couldn't parse a subscribe request — send help.
  const body = Mustache.render(replyHelpTpl, {})
  await sendReply(message, 'Re: Paper Picnic Subscription Help', body)
}

export default {
  // No HTTP surface: the worker runs on inbound email + cron only.
  fetch() {
    return new Response('Not found', { status: 404 })
  },
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runWeeklySend(env))
  },
  async email(message, env, ctx) {
    // Await (not waitUntil): setReject()/reply() must run within the handler's lifetime.
    await handleEmail(message, env)
  },
}
