// D1 reads/writes for subscriber records and their journal/preprint preferences.

import { deletePlunkContact } from '../lib/plunk.js'

export async function upsertSubscriber(email, journals, osf, env) {
  const row = await env.DB.prepare(
    `INSERT INTO subscribers (id, email, created_at) VALUES (?, ?, ?)
     ON CONFLICT(email) DO UPDATE SET email = excluded.email
     RETURNING id`
  ).bind(crypto.randomUUID(), email, new Date().toISOString()).first()

  const id = row.id

  const stmts = [
    env.DB.prepare('DELETE FROM journal_preferences WHERE subscriber_id = ?').bind(id),
    env.DB.prepare('DELETE FROM preprint_preferences WHERE subscriber_id = ?').bind(id),
  ]
  for (const jid of new Set(journals)) {
    stmts.push(env.DB.prepare('INSERT INTO journal_preferences (subscriber_id, journal_id) VALUES (?, ?)').bind(id, jid))
  }
  for (const cat of new Set(osf)) {
    stmts.push(env.DB.prepare('INSERT INTO preprint_preferences (subscriber_id, osf_category) VALUES (?, ?)').bind(id, cat))
  }

  await env.DB.batch(stmts)
}

export async function deleteSubscriber(email, env) {
  const sub = await env.DB.prepare(
    'SELECT id FROM subscribers WHERE email = ?'
  ).bind(email).first()
  if (!sub) return false

  await env.DB.batch([
    env.DB.prepare('DELETE FROM journal_preferences WHERE subscriber_id = ?').bind(sub.id),
    env.DB.prepare('DELETE FROM preprint_preferences WHERE subscriber_id = ?').bind(sub.id),
    env.DB.prepare('DELETE FROM subscribers WHERE id = ?').bind(sub.id),
  ])
  await deletePlunkContact(email, env)
  return true
}
