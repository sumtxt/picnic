/**
 * Unit tests for src/schedule/ (GitHub API mocked via globalThis.fetch).
 *
 * Run with: node --test tests/schedule.test.mjs
 * (from the worker/ directory)
 */

import { test, beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dispatchWorkflow } from '../src/schedule/dispatch.js'
import { CRON_JOBS } from '../src/schedule/jobs.js'
import { DIGEST_CRON } from '../src/digest/enqueue.js'

const env = { GITHUB_REPO: 'owner/repo', GH_DISPATCH_TOKEN: 'tok' }
const json = (body, status = 200) => new Response(JSON.stringify(body), { status })

// Replays `responses` in order and records every request.
let calls
function mockFetch(...responses) {
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url, method: init.method ?? 'GET', init })
    return responses.shift()
  }
}
beforeEach(() => { calls = [] })

test('dispatchWorkflow: dispatches when no run exists today', async () => {
  mockFetch(json({ total_count: 0 }), new Response(null, { status: 204 }))
  assert.equal(await dispatchWorkflow(env, 'crawl.yml'), 'dispatched')

  const today = new Date().toISOString().slice(0, 10)
  assert.equal(calls[0].url, `https://api.github.com/repos/owner/repo/actions/workflows/crawl.yml/runs?created=%3E%3D${today}&per_page=1`)
  assert.equal(calls[1].method, 'POST')
  assert.equal(calls[1].url, 'https://api.github.com/repos/owner/repo/actions/workflows/crawl.yml/dispatches')
  assert.deepEqual(JSON.parse(calls[1].init.body), { ref: 'main' })
  assert.equal(calls[1].init.headers.Authorization, 'Bearer tok')
})

test('dispatchWorkflow: skips when a run already exists today', async () => {
  mockFetch(json({ total_count: 1 }))
  assert.equal(await dispatchWorkflow(env, 'crawl.yml'), 'skipped')
  assert.equal(calls.length, 1)
})

test('dispatchWorkflow: does not dispatch if the run lookup fails', async () => {
  mockFetch(json({ message: 'Bad credentials' }, 401))
  await assert.rejects(dispatchWorkflow(env, 'crawl.yml'), /lookup failed with HTTP 401/)
  assert.equal(calls.length, 1)
})

test('dispatchWorkflow: throws on a failed dispatch, sent only once', async () => {
  mockFetch(json({ total_count: 0 }), json({}, 502))
  await assert.rejects(dispatchWorkflow(env, 'crawl.yml'), /dispatch failed with HTTP 502/)
  assert.equal(calls.filter(c => c.method === 'POST').length, 1)
})

test('wrangler.toml [triggers] crons: CRON_JOBS plus DIGEST_CRON', () => {
  const toml = readFileSync(new URL('../wrangler.toml', import.meta.url), 'utf8')
  const line = /^crons\s*=\s*\[(.*)\]/m.exec(toml)
  assert.ok(line, 'no crons = [...] line in wrangler.toml')
  const crons = [...line[1].matchAll(/"([^"]+)"/g)].map(m => m[1])
  assert.deepEqual(crons.sort(), [...Object.keys(CRON_JOBS), DIGEST_CRON].sort())
})

test('CRON_JOBS: every workflow file exists and allows workflow_dispatch', () => {
  for (const workflow of new Set(Object.values(CRON_JOBS))) {
    const path = new URL(`../../.github/workflows/${workflow}`, import.meta.url)
    assert.ok(readFileSync(path, 'utf8').includes('workflow_dispatch'), `${workflow} must allow workflow_dispatch`)
  }
})

test('crons name the day of the week (Cloudflare numbers days from 1 = Sunday)', () => {
  for (const cron of [...Object.keys(CRON_JOBS), DIGEST_CRON]) {
    assert.match(cron.split(' ')[4], /^[A-Z]{3}$/, `${cron}: use SUN-SAT, not numbers`)
  }
})
