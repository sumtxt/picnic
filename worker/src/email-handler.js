import { EmailMessage } from 'cloudflare:email'
import Mustache from 'mustache'
import PostalMime from 'postal-mime'
import { createMimeMessage } from 'mimetext'

import { extractBlock, parseSelections, stripTags } from './parse.js'
import { UNIVERSITY_DOMAINS } from './university-domains.js'

import replySubscribedTpl from '../templates/reply-subscribed.mustache'
import replyUnsubscribedTpl from '../templates/reply-unsubscribed.mustache'
import replyHelpTpl from '../templates/reply-help.mustache'
import replyNonUniversityTpl from '../templates/reply-nonuniversity.mustache'

const SUBSCRIBE_ADDRESS = 'subscribe@paper-picnic.com'
const UNSUBSCRIBE_ADDRESS = 'unsubscribe@paper-picnic.com'

function isUniversityEmail(email) {
  return UNIVERSITY_DOMAINS.has(email.toLowerCase().split('@')[1])
}

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

async function upsertSubscriber(email, journals, osf, env) {
  const existing = await env.DB.prepare(
    'SELECT id FROM subscribers WHERE email = ?'
  ).bind(email).first()

  const id = existing ? existing.id : crypto.randomUUID()
  const now = new Date().toISOString()
  const stmts = []

  if (existing) {
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

export async function handleEmail(message, env) {
  const parser = new PostalMime()
  const email = await parser.parse(message.raw)

  // DMARC check: use the TOPMOST Authentication-Results header (prepended by Cloudflare).
  // A sender can forge their own AR header, but it sits below Cloudflare's, so
  // headers.get() (which concatenates all) would be spoofable.
  const receiverAr = email.headers.find(h => h.key?.toLowerCase() === 'authentication-results')?.value ?? ''
  if (!/\bdmarc=pass\b/i.test(receiverAr)) {
    message.setReject('Could not verify sender domain (DMARC).')
    return
  }

  const from = (message.from || '').trim().toLowerCase()
  const to = (message.to || '').trim().toLowerCase()

  if (to === UNSUBSCRIBE_ADDRESS) {
    await deleteSubscriber(from, env)
    await sendReply(message, 'Re: Unsubscribed from Paper Picnic', Mustache.render(replyUnsubscribedTpl, {}))
    return
  }

  // Only subscribe@ is handled beyond this point — routing changes can't accidentally
  // make the Worker treat arbitrary mail as a subscription.
  if (to !== SUBSCRIBE_ADDRESS) return

  const bodyText = email.text || (email.html ? stripTags(email.html) : '')
  const block = extractBlock(bodyText)
  if (block) {
    const [journalsData, osfSubjectsData] = await Promise.all([
      env.KV.get('journals', 'json'),
      env.KV.get('osf_subjects', 'json'),
    ])

    const journalIds = new Set((journalsData ?? []).map(j => j.id))
    const osfIds = new Set((osfSubjectsData?.subgroups ?? []).map(sg => sg.id))
    const selections = parseSelections(block, { journalIds, osfIds })

    if (selections.journals.length > 0 || selections.osf.length > 0) {
      if (!isUniversityEmail(from)) {
        await sendReply(message, 'Re: Paper Picnic subscription', Mustache.render(replyNonUniversityTpl, {}))
        return
      }
      await upsertSubscriber(from, selections.journals, selections.osf, env)
      await sendReply(message, 'Re: Subscribed to Paper Picnic', Mustache.render(replySubscribedTpl, {}))
      return
    }
  }

  await sendReply(message, 'Re: Paper Picnic Subscription Help', Mustache.render(replyHelpTpl, {}))
}
