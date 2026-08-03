export { WeeklyDigestWorkflow } from './digest.js'
import { handleEmail } from './email-handler.js'

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
