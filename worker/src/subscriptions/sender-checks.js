// Checks on who sent an inbound message, run before any subscription change:
// DMARC verdict, sender domain, and RFC 3834 auto-reply detection.

import { UNIVERSITY_DOMAINS } from './university-domains.js'

// The domain is whatever follows the final '@'. Requires a non-empty local part,
// so a degenerate '@ucl.ac.uk' yields '' rather than a valid-looking domain.
export function emailDomain(email) {
  const at = email.lastIndexOf('@')
  return at > 0 ? email.slice(at + 1).toLowerCase() : ''
}

// Matches the domain itself or any subdomain of it (e.g., departmental subdomains)
export function isUniversityEmail(email) {
  const domain = emailDomain(email)
  if (!domain) return false
  let suffix = domain
  while (true) {
    if (UNIVERSITY_DOMAINS.has(suffix)) return true
    const dot = suffix.indexOf('.')
    if (dot === -1) return false
    suffix = suffix.slice(dot + 1)
  }
}

// RFC 3834: never auto-reply to auto-generated mail, or our reply and the other
// side's autoresponder ping-pong indefinitely.
export function isAutoSubmitted(message) {
  if (!message.from) return true // null envelope sender — a bounce

  const autoSubmitted = message.headers.get('Auto-Submitted')
  if (autoSubmitted && autoSubmitted.trim().toLowerCase() !== 'no') return true

  if (message.headers.get('X-Auto-Response-Suppress')) return true

  // Mailing-list traffic: a reply would go to the whole list.
  if (message.headers.get('List-Id') || message.headers.get('List-Unsubscribe')) return true

  const precedence = (message.headers.get('Precedence') || '').trim().toLowerCase()
  if (['bulk', 'list', 'junk', 'auto_reply'].includes(precedence)) return true

  // Older/vendor autoresponder markers predating RFC 3834
  if (message.headers.get('X-Autoreply')) return true
  if (message.headers.get('X-Autoreply-From')) return true
  if (message.headers.get('X-Autorespond')) return true

  const deliveredTo = (message.headers.get('Delivered-To') || '').trim().toLowerCase()
  return deliveredTo === 'autoresponder'
}

// Parses a receiver-stamped Authentication-Results header (RFC 8601) and returns
// { result, headerFrom } for its dmarc= method, or null if the header was not
// stamped by `expectedAuthservId` or carries no unambiguous dmarc= verdict.
//
// Substring matching (/dmarc=pass/) is unsafe here: properties such as
// smtp.mailfrom= and header.d= echo attacker-controlled text, and '=' is a legal
// atext character, so a sender whose local part is literally "dmarc=pass" would
// satisfy such a test while its real verdict was a failure.
export function parseAuthResults(value, expectedAuthservId) {
  if (!value || !expectedAuthservId) return null

  // Drop CFWS comments, e.g. "spf=fail (sender IP is 192.0.2.1)", which may
  // themselves contain '=' or ';'.
  const stripped = value.replace(/\([^)]*\)/g, ' ')

  // First field is "authserv-id [version]"; anything else is not Cloudflare's header.
  const authservId = stripped.split(';')[0].trim().split(/\s+/)[0].toLowerCase()
  if (authservId !== expectedAuthservId.toLowerCase()) return null

  // Anchor on the ';' property-list separator so the token cannot be matched
  // inside another method's value. Two verdicts means something injected one:
  // fail closed rather than guess which is the receiver's.
  const matches = [...stripped.matchAll(/(?:^|;)\s*dmarc\s*=\s*([a-z]+)([^;]*)/gi)]
  if (matches.length !== 1) return null

  const [, result, properties] = matches[0]
  const headerFrom = /\bheader\.from\s*=\s*"?([^\s;"]+)/i.exec(properties)

  return {
    result: result.toLowerCase(),
    headerFrom: headerFrom ? headerFrom[1].toLowerCase().replace(/\.$/, '') : null,
  }
}
