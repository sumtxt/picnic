/**
 * Unit tests for src/digest/ with in-memory KV, D1, queue and Plunk.
 *
 * Run with: node --test tests/digest.test.mjs
 * (from the worker/ directory)
 */

import { test, beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import { register } from 'node:module'

register('./helpers/mustache-loader.mjs', import.meta.url)
const { enqueueDigest } = await import('../src/digest/enqueue.js')
const { sendDigestBatch } = await import('../src/digest/send.js')

const today = new Date().toISOString().slice(0, 10)
const journals = [{ id: 'j1', name: 'Journal One', category: 'Political Science', category_rank: 1 }]
const publications = (update = today) => ({
  update,
  content: [{ journal_id: 'j1', journal_name: 'Journal One', articles: [{ title: 'A paper' }] }],
})

function fakeKv(values) {
  const puts = {}
  return {
    puts,
    async get(key) { return key in puts ? puts[key] : values[key] ?? null },
    async put(key, value) { puts[key] = value },
  }
}

function fakeDb({ subscribers, journalPrefs = [] }) {
  const stmt = (sql, args = []) => ({
    bind: (...a) => stmt(sql, a),
    async all() {
      if (sql.includes('last_sent_week IS NULL')) {
        return { results: subscribers.filter(s => s.last_sent_week !== args[0]).map(s => ({ id: s.id })) }
      }
      if (sql.includes('FROM subscribers')) return { results: subscribers.filter(s => args.includes(s.id)) }
      if (sql.includes('FROM journal_preferences')) return { results: journalPrefs.filter(p => args.includes(p.subscriber_id)) }
      return { results: [] }
    },
    async run() {
      const [week, id] = args
      subscribers.find(s => s.id === id).last_sent_week = week
    },
  })
  return { prepare: sql => stmt(sql), batch: stmts => Promise.all(stmts.map(s => s.all())) }
}

const message = body => ({
  body,
  state: null,
  ack() { this.state = 'ack' },
  retry() { this.state = 'retry' },
})

let plunkCalls
function mockPlunk(ok = true) {
  globalThis.fetch = async (url, init) => {
    plunkCalls.push(JSON.parse(init.body))
    return new Response('{}', { status: ok ? 200 : 500 })
  }
}
beforeEach(() => { plunkCalls = [] })

function digestEnv({ update = today, subscribers, journalPrefs }) {
  return {
    KV: fakeKv({ publications: publications(update), preprints: null, journals, osf_subjects: { subgroups: [] } }),
    DB: fakeDb({ subscribers, journalPrefs }),
    PLUNK_SECRET_KEY: 'test',
  }
}

// ---- sendDigestBatch ----

test('sendDigestBatch: sends, marks as sent and acks', async () => {
  mockPlunk()
  const subscribers = [{ id: 's1', email: 'a@uni.edu', last_sent_week: null }]
  const env = digestEnv({ subscribers, journalPrefs: [{ subscriber_id: 's1', journal_id: 'j1' }] })
  const msg = message({ subscriberId: 's1', issueKey: today })

  await sendDigestBatch({ messages: [msg] }, env)

  assert.equal(msg.state, 'ack')
  assert.equal(plunkCalls.length, 1)
  assert.equal(plunkCalls[0].to, 'a@uni.edu')
  assert.ok(plunkCalls[0].body.includes('A paper'))
  assert.ok(!plunkCalls[0].body.includes('No new papers'))
  assert.equal(subscribers[0].last_sent_week, today)
})

test('sendDigestBatch: skips subscribers already sent or unsubscribed', async () => {
  mockPlunk()
  const subscribers = [{ id: 'sent', email: 'b@uni.edu', last_sent_week: today }]
  const env = digestEnv({ subscribers, journalPrefs: [{ subscriber_id: 'sent', journal_id: 'j1' }] })
  const msgs = ['sent', 'gone'].map(id => message({ subscriberId: id, issueKey: today }))

  await sendDigestBatch({ messages: msgs }, env)

  assert.deepEqual(msgs.map(m => m.state), ['ack', 'ack'])
  assert.equal(plunkCalls.length, 0)
})

test('sendDigestBatch: sends a "no new papers" email for an empty selection', async () => {
  mockPlunk()
  const subscribers = [{ id: 'empty', email: 'c@uni.edu', last_sent_week: null }]
  const msg = message({ subscriberId: 'empty', issueKey: today })

  await sendDigestBatch({ messages: [msg] }, digestEnv({ subscribers, journalPrefs: [] }))

  assert.equal(msg.state, 'ack')
  assert.equal(plunkCalls.length, 1)
  assert.ok(plunkCalls[0].body.includes('No new papers'))
  assert.equal(subscribers[0].last_sent_week, today)
})

test('sendDigestBatch: retries when Plunk fails and does not mark as sent', async () => {
  mockPlunk(false)
  const subscribers = [{ id: 's1', email: 'a@uni.edu', last_sent_week: null }]
  const env = digestEnv({ subscribers, journalPrefs: [{ subscriber_id: 's1', journal_id: 'j1' }] })
  const msg = message({ subscriberId: 's1', issueKey: today })

  await sendDigestBatch({ messages: [msg] }, env)

  assert.equal(msg.state, 'retry')
  assert.equal(subscribers[0].last_sent_week, null)
})

test('sendDigestBatch: retries while KV holds an older issue, drops messages for an older issue', async () => {
  mockPlunk()
  const subscribers = [{ id: 's1', email: 'a@uni.edu', last_sent_week: null }]
  const journalPrefs = [{ subscriber_id: 's1', journal_id: 'j1' }]

  const early = message({ subscriberId: 's1', issueKey: '2999-01-01' })
  await sendDigestBatch({ messages: [early] }, digestEnv({ subscribers, journalPrefs }))
  assert.equal(early.state, 'retry')

  const stale = message({ subscriberId: 's1', issueKey: '2000-01-01' })
  await sendDigestBatch({ messages: [stale] }, digestEnv({ subscribers, journalPrefs }))
  assert.equal(stale.state, 'ack')

  assert.equal(plunkCalls.length, 0)
})

// ---- enqueueDigest ----

function enqueueEnv({ issue = today, enqueued = null, subscribers }) {
  const sent = []
  return {
    sent,
    KV: fakeKv({ issue, digest_enqueued: enqueued }),
    DB: fakeDb({ subscribers }),
    DIGEST_QUEUE: { async sendBatch(msgs) { sent.push(msgs) } },
  }
}

const manySubscribers = n => Array.from({ length: n }, (_, i) => ({ id: `s${i}`, last_sent_week: null }))

test('enqueueDigest: queues unsent subscribers once, in chunks of 100', async () => {
  const subscribers = [...manySubscribers(150), { id: 'done', last_sent_week: today }]
  const env = enqueueEnv({ subscribers })

  await enqueueDigest(env)

  assert.deepEqual(env.sent.map(b => b.length), [100, 50])
  assert.deepEqual(env.sent[0][0].body, { subscriberId: 's0', issueKey: today })
  assert.equal(env.KV.puts.digest_enqueued, today)

  await enqueueDigest(env)
  assert.equal(env.sent.length, 2)
})

test('enqueueDigest: does nothing until KV holds today\'s issue', async () => {
  const env = enqueueEnv({ issue: '2000-01-01', subscribers: manySubscribers(3) })
  await enqueueDigest(env)
  assert.equal(env.sent.length, 0)
})

test('enqueueDigest: does nothing if the issue was already queued', async () => {
  const env = enqueueEnv({ enqueued: today, subscribers: manySubscribers(3) })
  await enqueueDigest(env)
  assert.equal(env.sent.length, 0)
})
