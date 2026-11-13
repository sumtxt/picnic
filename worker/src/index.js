// Entry point for the Paper Picnic worker. Each Cloudflare event type is routed
// to the feature that owns it:
//   email     → subscriptions/  (subscribe@ / unsubscribe@ inbound mail)
//   scheduled → schedule/       (crons in wrangler.toml [triggers] start GitHub
//                                Actions workflows; see schedule/jobs.js)
// The weekly digest runs as a Cloudflare Workflow (digest/workflow.js), started
// from GitHub Actions after the crawl has pushed fresh data to KV.

export { WeeklyDigestWorkflow } from './digest/workflow.js'
import { handleEmail } from './subscriptions/handler.js'
import { dispatchWorkflow } from './schedule/dispatch.js'
import { CRON_JOBS } from './schedule/jobs.js'

export default {
  fetch() {
    return new Response('Not found', { status: 404 })
  },
  async scheduled(event, env, ctx) {
    const workflow = CRON_JOBS[event.cron]
    if (!workflow) {
      console.error(`scheduled: no workflow mapped to cron "${event.cron}"`)
      return
    }
    ctx.waitUntil(dispatchWorkflow(env, workflow))
  },
  async email(message, env, ctx) {
    // Await (not waitUntil): setReject()/reply() must run within the handler's lifetime.
    await handleEmail(message, env)
  },
}
