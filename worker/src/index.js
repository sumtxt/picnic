// Entry point for the Paper Picnic worker. Each Cloudflare event type is routed
// to the feature that owns it:
//   email     → subscriptions/  (subscribe@ / unsubscribe@ inbound mail)
//   scheduled → digest/enqueue.js for the digest cron, otherwise schedule/
//               (start GitHub Actions workflows; see schedule/jobs.js)
//   queue     → digest/send.js  (send the digest, one small batch at a time)

import { handleEmail } from './subscriptions/handler.js'
import { dispatchWorkflow } from './schedule/dispatch.js'
import { CRON_JOBS } from './schedule/jobs.js'
import { DIGEST_CRON, enqueueDigest } from './digest/enqueue.js'
import { sendDigestBatch } from './digest/send.js'

export default {
  fetch() {
    return new Response('Not found', { status: 404 })
  },
  async scheduled(event, env, ctx) {
    if (event.cron === DIGEST_CRON) {
      ctx.waitUntil(enqueueDigest(env))
      return
    }
    const workflow = CRON_JOBS[event.cron]
    if (!workflow) {
      console.error(`scheduled: no job for cron "${event.cron}"`)
      return
    }
    ctx.waitUntil(dispatchWorkflow(env, workflow))
  },
  async queue(batch, env) {
    await sendDigestBatch(batch, env)
  },
  async email(message, env, ctx) {
    // Await (not waitUntil): setReject()/reply() must run within the handler's lifetime.
    await handleEmail(message, env)
  },
}
