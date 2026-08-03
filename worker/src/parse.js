/**
 * Parse inbound email text for #PICNIC subscription blocks.
 */

/**
 * Extract the #PICNIC block from raw email text.
 * Looks for lines matching /#\s*PICNIC(?:\s*v\d+)?\s*BEGIN/i and /#\s*PICNIC\s*END/i.
 * If no END marker is found the slice runs to the end of the string.
 * Returns the text between the markers (exclusive), or null if no BEGIN is found.
 *
 * @param {string} text  Plain-text email body (prefer text/plain, fall back to tag-stripped HTML)
 * @returns {string|null}
 */
export function extractBlock(text) {
  if (!text) return null

  const beginRe = /#\s*PICNIC(?:\s*v\d+)?\s*BEGIN/i
  const endRe = /#\s*PICNIC\s*END/i

  const beginMatch = beginRe.exec(text)
  if (!beginMatch) return null

  const afterBegin = text.slice(beginMatch.index + beginMatch[0].length)
  const endMatch = endRe.exec(afterBegin)

  const block = endMatch ? afterBegin.slice(0, endMatch.index) : afterBegin
  return block
}

/**
 * Parse a #PICNIC block into a selections object.
 *
 * Each non-blank line is expected to be `key: value` or `key = value`.
 * The value is split on /[\s,()]+/ and each token is whitelisted against
 * the known journal-id and osf-id Sets.  Unknown tokens are silently dropped.
 *
 * Recognised keys (case-insensitive, aliases supported):
 *   journal | j                    → journal IDs
 *   preprint | osf | p             → OSF subgroup IDs
 * (An `action:` line, if present, is ignored — intent is decided by the
 * recipient address, not the block contents.)
 *
 * @param {string|null} block           The raw block text (from extractBlock)
 * @param {{ journalIds: Set<string>, osfIds: Set<string> }} known
 * @returns {{ journals: string[], osf: string[] }}
 */
export function parseSelections(block, known) {
  const result = { journals: [], osf: [] }
  if (!block) return result

  const { journalIds, osfIds } = known

  for (const rawLine of block.split('\n')) {
    const line = rawLine.trim()
    if (!line) continue

    // Split on first `:` or `=`
    const sepMatch = /^([^:=]+)[:=](.*)$/.exec(line)
    if (!sepMatch) continue

    const key = sepMatch[1].trim().toLowerCase()
    const rawVal = sepMatch[2]

    // Split value on whitespace, commas, parentheses (handles "(Human Name)" annotations)
    const tokens = rawVal.split(/[\s,()]+/).map(t => t.trim()).filter(Boolean)

    if (key === 'journal' || key === 'j') {
      for (const tok of tokens) {
        if (journalIds.has(tok)) result.journals.push(tok)
      }
      continue
    }

    if (key === 'preprint' || key === 'osf' || key === 'p') {
      for (const tok of tokens) {
        if (osfIds.has(tok)) result.osf.push(tok)
      }
      continue
    }
    // Unknown key — silently ignore (e.g. "Tel: +44 20 7946 0000")
  }

  return result
}

/**
 * Strip HTML tags from a string (minimal, no external deps).
 * Used as a fallback when no text/plain part is available.
 *
 * @param {string} html
 * @returns {string}
 */
export function stripTags(html) {
  // Replace block-level tags with newlines so structure is preserved
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
