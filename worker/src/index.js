import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { UNIVERSITY_DOMAINS } from './university-domains.js'

const BATCH_SIZE = 10

const PUBLICATIONS_URL = 'https://raw.githubusercontent.com/sumtxt/picnic/main/output/publications.json'
const PREPRINTS_URL = 'https://raw.githubusercontent.com/sumtxt/picnic/main/output/preprints.json'
const JOURNALS_URL = 'https://raw.githubusercontent.com/sumtxt/picnic/main/parameters/journals.json'
const OSF_SUBJECTS_URL = 'https://raw.githubusercontent.com/sumtxt/picnic/main/parameters/osf_subjects.json'

const app = new Hono()

app.use('/api/*', cors({
  origin: ['https://www.paper-picnic.com', 'https://paper-picnic.com'],
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowHeaders: ['Content-Type'],
}))

// --- Helpers ---

function isUniversityEmail(email) {
  const parts = email.toLowerCase().split('@')
  if (parts.length !== 2) return false
  return UNIVERSITY_DOMAINS.has(parts[1])
}

async function sendPlunkEmail(to, subject, body, env) {
  const resp = await fetch('https://next-api.useplunk.com/v1/send', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.PLUNK_SECRET_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ to, from: 'noreply@paper-picnic.com', subject, body, subscribed: false }),
  })
  if (!resp.ok) {
    const text = await resp.text()
    console.error('Plunk error:', resp.status, text)
  }
  return resp.ok
}

async function sendConfirmationEmail(email, token, env) {
  const confirmUrl = `https://api.paper-picnic.com/api/confirm?token=${token}`
  const body = `
<p>Thanks for signing up for personalized Paper Picnic email alerts!</p>
<p>Please confirm your subscription by clicking the link below:</p>
<p><a href="${confirmUrl}">Confirm my subscription</a></p>
<p>If the link does not work, copy and paste this URL into your browser:<br>${confirmUrl}</p>
<p>If you did not request this, you can safely ignore this email.</p>
<p style="color:#666;font-size:0.9em;">— Paper Picnic &lt;paper-picnic.com&gt;</p>
`
  return sendPlunkEmail(email, 'Confirm your Paper Picnic subscription', body, env)
}

// --- Routes ---

// POST /api/subscribe
// Body: { email, journals: string[], osf_categories: string[] }
app.post('/api/subscribe', async (c) => {
  let body
  try {
    body = await c.req.json()
  } catch {
    return c.json({ error: 'Invalid JSON body' }, 400)
  }

  const { email, journals = [], osf_categories = [] } = body

  if (!email || typeof email !== 'string' || !email.includes('@')) {
    return c.json({ error: 'Invalid email address.' }, 400)
  }

  if (!isUniversityEmail(email)) {
    return c.json({
      error: 'Only university email addresses are accepted. Please use your institutional email (e.g. name@university.edu or name@institution.ac.uk).'
    }, 403)
  }

  if (journals.length === 0 && osf_categories.length === 0) {
    return c.json({ error: 'Please select at least one journal or preprint category.' }, 400)
  }

  const db = c.env.DB
  const existing = await db.prepare(
    'SELECT id, token, confirmed FROM subscribers WHERE email = ?'
  ).bind(email).first()

  if (existing) {
    if (existing.confirmed) {
      return c.json({ error: 'This email is already subscribed. Check your inbox for a preferences management link, or contact hello@paper-picnic.com.' }, 409)
    }
    await sendConfirmationEmail(email, existing.token, c.env)
    return c.json({ message: 'A confirmation email has been resent. Please check your inbox.' })
  }

  const id = crypto.randomUUID()
  const token = crypto.randomUUID()
  const now = new Date().toISOString()

  const stmts = [
    db.prepare('INSERT INTO subscribers (id, email, token, confirmed, created_at) VALUES (?, ?, ?, 0, ?)').bind(id, email, token, now),
    ...journals.map(jid => db.prepare('INSERT INTO journal_preferences (subscriber_id, journal_id) VALUES (?, ?)').bind(id, jid)),
    ...osf_categories.map(cat => db.prepare('INSERT INTO preprint_preferences (subscriber_id, osf_category) VALUES (?, ?)').bind(id, cat)),
  ]

  await db.batch(stmts)
  await sendConfirmationEmail(email, token, c.env)

  return c.json({ message: 'Please check your email to confirm your subscription.' })
})

// GET /api/confirm?token= — show confirmation page (do not confirm yet, defeats link scanners)
app.get('/api/confirm', async (c) => {
  const token = c.req.query('token')
  if (!token) return c.json({ error: 'Missing token' }, 400)

  const sub = await c.env.DB.prepare(
    'SELECT confirmed FROM subscribers WHERE token = ?'
  ).bind(token).first()

  if (!sub) {
    return c.html(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Paper Picnic</title></head><body style="font-family:sans-serif;max-width:480px;margin:4rem auto;padding:0 1rem">
<h2>Invalid link</h2><p>This confirmation link is invalid or has expired.</p></body></html>`, 404)
  }

  if (sub.confirmed) {
    return c.html(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Paper Picnic</title></head><body style="font-family:sans-serif;max-width:480px;margin:4rem auto;padding:0 1rem">
<h2>Already confirmed</h2><p>Your subscription is already active. You can <a href="https://www.paper-picnic.com/preferences?token=${token}">manage your preferences</a> at any time.</p></body></html>`)
  }

  return c.html(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Confirm subscription — Paper Picnic</title></head><body style="font-family:sans-serif;max-width:480px;margin:4rem auto;padding:0 1rem">
<h2>Confirm your subscription</h2>
<p>Click the button below to activate your Paper Picnic email alerts.</p>
<form method="POST" action="/api/confirm?token=${token}">
  <button type="submit" style="background:#2563eb;color:#fff;border:none;padding:0.75rem 1.5rem;font-size:1rem;border-radius:4px;cursor:pointer">Confirm subscription</button>
</form>
</body></html>`)
})

// POST /api/confirm?token= — actually confirm
app.post('/api/confirm', async (c) => {
  const token = c.req.query('token')
  if (!token) return c.json({ error: 'Missing token' }, 400)

  const result = await c.env.DB.prepare(
    'UPDATE subscribers SET confirmed = 1 WHERE token = ? AND confirmed = 0'
  ).bind(token).run()

  if (result.meta.changes === 0) {
    return c.redirect('https://www.paper-picnic.com/subscribe?status=already_confirmed')
  }

  return c.redirect('https://www.paper-picnic.com/subscribe?status=confirmed')
})

// DELETE /api/unsubscribe?token=
app.delete('/api/unsubscribe', async (c) => {
  const token = c.req.query('token')
  if (!token) return c.json({ error: 'Missing token' }, 400)

  const result = await c.env.DB.prepare(
    'DELETE FROM subscribers WHERE token = ?'
  ).bind(token).run()

  if (result.meta.changes === 0) {
    return c.json({ error: 'Invalid or expired token.' }, 404)
  }

  return c.json({ message: 'You have been unsubscribed. All your data has been deleted.' })
})

// GET /api/preferences?token=
app.get('/api/preferences', async (c) => {
  const token = c.req.query('token')
  if (!token) return c.json({ error: 'Missing token' }, 400)

  const sub = await c.env.DB.prepare(
    'SELECT id FROM subscribers WHERE token = ? AND confirmed = 1'
  ).bind(token).first()

  if (!sub) return c.json({ error: 'Invalid token or unconfirmed subscription.' }, 404)

  const [journals, osf] = await c.env.DB.batch([
    c.env.DB.prepare('SELECT journal_id FROM journal_preferences WHERE subscriber_id = ?').bind(sub.id),
    c.env.DB.prepare('SELECT osf_category FROM preprint_preferences WHERE subscriber_id = ?').bind(sub.id),
  ])

  return c.json({
    journals: journals.results.map(r => r.journal_id),
    osf_categories: osf.results.map(r => r.osf_category),
  })
})

// PUT /api/preferences?token=
// Body: { journals: string[], osf_categories: string[] }
app.put('/api/preferences', async (c) => {
  const token = c.req.query('token')
  if (!token) return c.json({ error: 'Missing token' }, 400)

  const sub = await c.env.DB.prepare(
    'SELECT id FROM subscribers WHERE token = ? AND confirmed = 1'
  ).bind(token).first()

  if (!sub) return c.json({ error: 'Invalid token or unconfirmed subscription.' }, 404)

  let body
  try {
    body = await c.req.json()
  } catch {
    return c.json({ error: 'Invalid JSON body' }, 400)
  }

  const { journals = [], osf_categories = [] } = body

  if (journals.length === 0 && osf_categories.length === 0) {
    return c.json({ error: 'Please select at least one journal or preprint category.' }, 400)
  }

  const db = c.env.DB
  await db.batch([
    db.prepare('DELETE FROM journal_preferences WHERE subscriber_id = ?').bind(sub.id),
    db.prepare('DELETE FROM preprint_preferences WHERE subscriber_id = ?').bind(sub.id),
    ...journals.map(jid => db.prepare('INSERT INTO journal_preferences (subscriber_id, journal_id) VALUES (?, ?)').bind(sub.id, jid)),
    ...osf_categories.map(cat => db.prepare('INSERT INTO preprint_preferences (subscriber_id, osf_category) VALUES (?, ?)').bind(sub.id, cat)),
  ])

  return c.json({ message: 'Preferences updated.' })
})

// --- Weekly send (cron) ---

function escapeHtml(str) {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

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
      const article_count = journals.reduce((s, j) => s + j.articles.length, 0)
      return {
        id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
        name,
        journal_count: journals.length,
        article_count,
        journals,
      }
    })
}

function buildPreprintsSection(preprints, subgroupMap, subscriberOsfCategories) {
  if (!preprints || !preprints.content || subscriberOsfCategories.length === 0) return null
  const selected = new Set(subscriberOsfCategories)
  const groups = []
  let preprint_count = 0
  for (const group of preprints.content) {
    if (!selected.has(group.id)) continue
    if (!group.items || group.items.length === 0) continue
    groups.push({ group_name: subgroupMap[group.id] || group.id, items: group.items })
    preprint_count += group.items.length
  }
  if (groups.length === 0) return null
  return { groups, preprint_count }
}

function buildEmailHtml({ disciplines, preprints_content, preferences_url, unsubscribe_url }) {
  const prefsHref = escapeHtml(preferences_url)
  const unsubHref = escapeHtml(unsubscribe_url)

  let html = `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Paper Picnic - New Baskets</title></head><body>`
  html += `<p>New baskets with the latest published research are available on <a href="https://paper-picnic.com">paper-picnic.com</a>.</p>`
  html += `<p>This email contains only the journals and preprint categories you selected. You can <a href="${prefsHref}">update your preferences</a> or <a href="${unsubHref}">unsubscribe</a> at any time.</p>`
  html += `<hr>`

  for (const disc of disciplines) {
    html += `<h2 id="${escapeHtml(disc.id)}">${escapeHtml(disc.name)}</h2>`
    html += `<p><em>${disc.journal_count} journals · ${disc.article_count} new papers</em></p>`
    for (const journal of disc.journals) {
      html += `<div><h3>${escapeHtml(journal.journal_name)}</h3>`
      for (const article of journal.articles) {
        html += `<div><div><a href="${escapeHtml(article.doi)}">${escapeHtml(article.title)}</a></div>`
        html += `<div><em>${escapeHtml(article.authors)}</em></div>`
        if (article.abstract) {
          html += `<div style="font-size:0.9em;color:#333;">${escapeHtml(article.abstract)}</div>`
        }
        html += `<p></p></div>`
      }
      html += `</div>`
    }
  }

  if (preprints_content) {
    html += `<h2 id="preprints">Preprints (SocArXiv / OSF)</h2>`
    html += `<p><em>${preprints_content.preprint_count} new preprints</em></p>`
    for (const group of preprints_content.groups) {
      html += `<h3>${escapeHtml(group.group_name)}</h3>`
      for (const item of group.items) {
        html += `<div><div><a href="${escapeHtml(item.url)}">${escapeHtml(item.title)}</a></div>`
        html += `<div><em>${escapeHtml(item.authors)}</em></div>`
        if (item.abstract) {
          html += `<div style="font-size:0.9em;color:#333;">${escapeHtml(item.abstract)}</div>`
        }
        html += `<p></p></div>`
      }
    }
  }

  html += `<hr><p style="font-size:0.85em;color:#666;">You are receiving this email because you subscribed to personalized Paper Picnic alerts.<br><a href="${prefsHref}">Manage preferences</a> · <a href="${unsubHref}">Unsubscribe</a></p>`
  html += `</body></html>`
  return html
}

async function runWeeklySend(env) {
  // Quick pre-check using only D1: any subscriber that hasn't received something in 6+ days?
  // Avoids fetching publications.json on the 6 idle days between issues.
  const staleRow = await env.DB.prepare(
    "SELECT COUNT(*) as cnt FROM subscribers WHERE confirmed = 1 AND (last_sent_week IS NULL OR last_sent_week < date('now', '-6 days'))"
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
    'SELECT id, email, token FROM subscribers WHERE confirmed = 1 AND (last_sent_week IS NULL OR last_sent_week != ?) LIMIT ?'
  ).bind(issueKey, BATCH_SIZE).all()
  if (pending.results.length === 0) return

  // Fetch supporting data in parallel (all I/O, no CPU cost)
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

  // Send emails sequentially (respects the 6-simultaneous-connections limit)
  for (const sub of pending.results) {
    const disciplines = buildDisciplineSections(
      publications.content, journalMap, journalsBySub[sub.id] || []
    )
    const preprintsContent = buildPreprintsSection(
      preprints, subgroupMap, osfBySub[sub.id] || []
    )
    if (disciplines.length > 0 || preprintsContent) {
      const html = buildEmailHtml({
        disciplines,
        preprints_content: preprintsContent,
        preferences_url: `https://www.paper-picnic.com/preferences?token=${sub.token}`,
        unsubscribe_url: `https://api.paper-picnic.com/api/unsubscribe?token=${sub.token}`,
      })
      await sendPlunkEmail(sub.email, subject, html, env)
    }
  }

  // Mark this entire batch as sent for this issue (skip subscribers had no matching content too)
  await env.DB.batch(
    ids.map(id =>
      env.DB.prepare('UPDATE subscribers SET last_sent_week = ? WHERE id = ?').bind(issueKey, id)
    )
  )
}

export default {
  fetch: (req, env, ctx) => app.fetch(req, env, ctx),
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runWeeklySend(env))
  },
}
