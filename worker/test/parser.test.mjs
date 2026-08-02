/**
 * Unit tests for extractBlock / parseSelections in src/parse.js
 *
 * Run with: node --test test/parser.test.mjs
 * (from the worker/ directory)
 */

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { extractBlock, parseSelections, stripTags } from '../src/parse.js'

// ---- known ID sets used in all parseSelections tests ----
const journalIds = new Set(['19312458', '10584609', '00219916'])
const osfIds = new Set(['c1a', 'c6a', 'c2b'])
const known = { journalIds, osfIds }

// ---- extractBlock tests ----

test('extractBlock: returns slice between markers', () => {
  const text = `Hi there,

#PICNIC v1 BEGIN
action: subscribe
journal: 19312458
#PICNIC END

Best regards`
  const block = extractBlock(text)
  assert.ok(block !== null, 'expected non-null block')
  assert.ok(block.includes('action: subscribe'))
  assert.ok(block.includes('19312458'))
  assert.ok(!block.includes('Hi there'))
  assert.ok(!block.includes('Best regards'))
})

test('extractBlock: tolerates missing END marker', () => {
  const text = `#PICNIC BEGIN
action: subscribe
journal: 19312458

Sent from my iPhone`
  const block = extractBlock(text)
  assert.ok(block !== null)
  assert.ok(block.includes('19312458'))
  // Everything after BEGIN included (no END to cut off)
  assert.ok(block.includes('Sent from my iPhone'))
})

test('extractBlock: returns null when no BEGIN marker', () => {
  const text = 'Hello, please subscribe me. journal: 19312458'
  assert.equal(extractBlock(text), null)
})

test('extractBlock: case-insensitive markers', () => {
  const text = '#picnic v2 begin\naction: subscribe\n#picnic end'
  const block = extractBlock(text)
  assert.ok(block !== null)
})

// ---- parseSelections tests ----

test('parseSelections: parses subscribe with journals and osf', () => {
  const block = `
action: subscribe
journal: 19312458   (Communication Methods and Measures)
journal: 10584609   (Political Communication)
preprint: c6a       (Sociology)
`
  const result = parseSelections(block, known)
  assert.equal(result.action, 'subscribe')
  assert.deepEqual(result.journals.sort(), ['10584609', '19312458'])
  assert.deepEqual(result.osf, ['c6a'])
})

test('parseSelections: parses unsubscribe action', () => {
  const block = 'action: unsubscribe\n'
  const result = parseSelections(block, known)
  assert.equal(result.action, 'unsubscribe')
})

test('parseSelections: drops unknown journal IDs (whitelist)', () => {
  const block = `
action: subscribe
journal: 99999999
journal: 19312458
`
  const result = parseSelections(block, known)
  assert.deepEqual(result.journals, ['19312458'])
})

test('parseSelections: drops unknown osf IDs (whitelist)', () => {
  const block = `
action: subscribe
preprint: xyz
preprint: c1a
`
  const result = parseSelections(block, known)
  assert.deepEqual(result.osf, ['c1a'])
})

test('parseSelections: ignores stray key: value signature lines', () => {
  // Simulate a realistic auto-signature that leaks into the block
  // (e.g. if END marker is missing and the signature contains key-like lines)
  const block = `
action: subscribe
journal: 19312458
Tel: +44 20 7946 0000
Fax: +44 20 7946 0001
Address: 123 Example Street
`
  const result = parseSelections(block, known)
  assert.deepEqual(result.journals, ['19312458'])
  assert.equal(result.osf.length, 0)
})

test('parseSelections: accepts = as separator', () => {
  const block = `
action = subscribe
journal = 19312458
`
  const result = parseSelections(block, known)
  assert.equal(result.action, 'subscribe')
  assert.deepEqual(result.journals, ['19312458'])
})

test('parseSelections: j and p aliases', () => {
  const block = `
action: subscribe
j: 19312458
p: c6a
`
  const result = parseSelections(block, known)
  assert.deepEqual(result.journals, ['19312458'])
  assert.deepEqual(result.osf, ['c6a'])
})

test('parseSelections: null block returns empty result', () => {
  const result = parseSelections(null, known)
  assert.equal(result.action, null)
  assert.deepEqual(result.journals, [])
  assert.deepEqual(result.osf, [])
})

// ---- HTML-only body fallback via stripTags ----

test('stripTags: strips HTML tags leaving text content', () => {
  const html = '<p>Hello</p><div><a href="x">World</a></div>'
  const text = stripTags(html)
  assert.ok(!text.includes('<'))
  assert.ok(text.includes('Hello'))
  assert.ok(text.includes('World'))
})

test('Full pipeline: HTML-only email with #PICNIC block', () => {
  const html = `<p>Please subscribe me.</p>
<pre>
#PICNIC v1 BEGIN
action: subscribe
journal: 00219916
preprint: c2b
#PICNIC END
</pre>
<p>Best,<br>Alex</p>`

  const strippedText = stripTags(html)
  const block = extractBlock(strippedText)
  assert.ok(block !== null, 'expected block from stripped HTML')

  const result = parseSelections(block, known)
  assert.equal(result.action, 'subscribe')
  assert.deepEqual(result.journals, ['00219916'])
  assert.deepEqual(result.osf, ['c2b'])
})
