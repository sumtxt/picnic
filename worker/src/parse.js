// Looks for #PICNIC BEGIN ... #PICNIC END markers (END is optional).
export function extractBlock(text) {
  if (!text) return null
  const beginMatch = /#\s*PICNIC(?:\s*v\d+)?\s*BEGIN/i.exec(text)
  if (!beginMatch) return null
  const afterBegin = text.slice(beginMatch.index + beginMatch[0].length)
  const endMatch = /#\s*PICNIC\s*END/i.exec(afterBegin)
  return endMatch ? afterBegin.slice(0, endMatch.index) : afterBegin
}

// Parses key: value lines from a #PICNIC block.
// Recognised keys: journal | j → journal IDs,  preprint | osf | p → OSF subgroup IDs.
// Values are split on whitespace/commas/parens to handle "(Human Name)" annotations.
// Unknown keys (e.g. email signatures) are silently ignored.
export function parseSelections(block, { journalIds, osfIds }) {
  const result = { journals: [], osf: [] }
  if (!block) return result

  const keyMap = {
    journal: [journalIds, result.journals],
    j:       [journalIds, result.journals],
    preprint: [osfIds, result.osf],
    osf:     [osfIds, result.osf],
    p:       [osfIds, result.osf],
  }

  for (const rawLine of block.split('\n')) {
    const line = rawLine.trim()
    if (!line) continue
    const sepMatch = /^([^:=]+)[:=](.*)$/.exec(line)
    if (!sepMatch) continue

    const entry = keyMap[sepMatch[1].trim().toLowerCase()]
    if (!entry) continue

    const [ids, arr] = entry
    for (const tok of sepMatch[2].split(/[\s,()]+/).map(t => t.trim()).filter(Boolean)) {
      if (ids.has(tok)) arr.push(tok)
    }
  }

  return result
}

// Strips HTML tags; replaces block-level elements with newlines to preserve structure.
export function stripTags(html) {
  return html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/?(p|div|li|tr|td|th|h[1-6])[^>]*>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
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
