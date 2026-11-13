// Entry point for the Paper Picnic worker. Each Cloudflare event type is routed
// to the feature that owns it:
//   email     → subscriptions/  (subscribe@ / unsubscribe@ inbound mail)
//   scheduled → digest/         (see wrangler.toml [triggers])
// The weekly digest itself runs as a Cloudflare Workflow (digest/workflow.js),
// triggered from GitHub Actions after the crawl has pushed fresh data to KV.

export { WeeklyDigestWorkflow } from './digest/workflow.js'
import { handleEmail } from './subscriptions/handler.js'

export default {
  fetch() {
    return new Response('Not found', { status: 404 })
  },
  async scheduled(event, env, ctx) {
    ctx.waitUntil(env.WEEKLY_DIGEST.create())
  },
  async email(message, env, ctx) {
    // Await (not waitUntil): setReject()/reply() must run within the handler's lifetime.
    await handleEmail(message, env)
  },
}
