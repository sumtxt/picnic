import { EmailMessage } from 'cloudflare:email'
import Mustache from 'mustache'
import PostalMime from 'postal-mime'
import { createMimeMessage } from 'mimetext'

import { extractBlock, parseSelections, stripTags } from './selections.js'
import { emailDomain, isAutoSubmitted, isUniversityEmail, parseAuthResults } from './sender-checks.js'
import { deleteSubscriber, upsertSubscriber } from './store.js'

import replySubscribedTpl from '../../templates/replies/subscribed.mustache'
import replyUnsubscribedTpl from '../../templates/replies/unsubscribed.mustache'
import replyHelpTpl from '../../templates/replies/help.mustache'
import replyNonUniversityTpl from '../../templates/replies/nonuniversity.mustache'
import replyTryAgainTpl from '../../templates/replies/tryagain.mustache'

const SUBSCRIBE_ADDRESS = 'subscribe@paper-picnic.com'
const UNSUBSCRIBE_ADDRESS = 'unsubscribe@paper-picnic.com'

// authserv-id that Cloudflare Email Routing stamps on the Authentication-Results
// header it prepends. If this is wrong, EVERY message is rejected — the mismatch
// is logged with the observed id so it is a one-line fix.
const CF_AUTHSERV_ID = 'mx.cloudflare.net'

async function sendReply(message, subject, body) {
  const msg = createMimeMessage()

  const messageId = message.headers.get('Message-ID')
  if (messageId) {
    msg.setHeader('In-Reply-To', messageId)
    const incomingReferences = message.headers.get('References')
    msg.setHeader('References', incomingReferences ? `${incomingReferences} ${messageId}` : messageId)
  }

  // RFC 3834: mark the reply so a well-behaved autoresponder does not answer it.
  msg.setHeader('Auto-Submitted', 'auto-replied')
  msg.setHeader('X-Auto-Response-Suppress', 'All')

  // Sender must be on the same domain that received the mail; use the exact To address.
  msg.setSender({ name: 'Paper Picnic', addr: message.to })
  msg.setRecipient(message.from)
  msg.setSubject(subject)
  msg.addMessage({ contentType: 'text/plain', data: body })

  await message.reply(new EmailMessage(message.to, message.from, msg.asRaw()))
}

export async function handleEmail(message, env) {
  const parser = new PostalMime()
  const email = await parser.parse(message.raw)

  // DMARC check: use the TOPMOST Authentication-Results header (prepended by Cloudflare).
  // A sender can forge their own AR header, but it sits below Cloudflare's, so
  // headers.get() (which concatenates all) would be spoofable.
  const receiverAr = email.headers.find(h => h.key?.toLowerCase() === 'authentication-results')?.value ?? ''
  const dmarc = parseAuthResults(receiverAr, CF_AUTHSERV_ID)
  if (!dmarc) {
    // Log the observed authserv-id only — the rest of the header carries the
    // sender's address.
    const observed = receiverAr.split(';')[0].trim() || '(none)'
    console.error(`Rejected: no usable Authentication-Results from ${CF_AUTHSERV_ID}, saw: ${observed}`)
    message.setReject('Could not verify sender domain (DMARC).')
    return
  }
  if (dmarc.result !== 'pass' || !dmarc.headerFrom) {
    message.setReject('Could not verify sender domain (DMARC).')
    return
  }

  // Authorise on the identity DMARC actually validated: the RFC 5322 From header,
  // whose domain must equal the header.from= Cloudflare reported passing.
  // message.from is the SMTP envelope sender, which DMARC does not authenticate —
  // a DKIM-aligned message can name any address there, including a victim's.
  const from = (email.from?.address || '').trim().toLowerCase()
  if (!from || emailDomain(from) !== dmarc.headerFrom) {
    message.setReject('Sender address does not match the DMARC-verified domain.')
    return
  }

  // The reply is delivered to the envelope sender, so require it to match the
  // verified From exactly. Otherwise a DKIM-aligned message could still aim our
  // reply — and the subscription it confirms — at an unrelated address.
  if ((message.from || '').trim().toLowerCase() !== from) {
    message.setReject('Envelope sender does not match the verified From address.')
    return
  }

  // Drop rather than setReject: rejecting generates a bounce, which is more mail.
  if (isAutoSubmitted(message)) {
    console.log('Ignoring auto-submitted message')
    return
  }

  const to = (message.to || '').trim().toLowerCase()

  if (to === UNSUBSCRIBE_ADDRESS) {
    try {
      await deleteSubscriber(from, env)
    } catch (err) {
      console.error('deleteSubscriber failed:', err)
      await sendReply(message, 'Re: Paper Picnic unsubscribe', Mustache.render(replyTryAgainTpl, {}))
      return
    }
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
      try {
        await upsertSubscriber(from, selections.journals, selections.osf, env)
      } catch (err) {
        console.error('upsertSubscriber failed:', err)
        await sendReply(message, 'Re: Paper Picnic subscription', Mustache.render(replyTryAgainTpl, {}))
        return
      }
      await sendReply(message, 'Re: Subscribed to Paper Picnic', Mustache.render(replySubscribedTpl, {}))
      return
    }
  }

  await sendReply(message, 'Re: Paper Picnic Subscription Help', Mustache.render(replyHelpTpl, {}))
}
