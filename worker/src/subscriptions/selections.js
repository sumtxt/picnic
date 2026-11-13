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
