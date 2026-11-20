// Queues one message per subscriber not yet sent the current issue. Runs every
// 15 minutes on Fridays and acts once per issue, as soon as the KV key `issue`
// (written last by push-to-cloudflare.yml) holds today's date.

export const DIGEST_CRON = '*/15 * * * FRI'

export async function enqueueDigest(env) {
  const issueKey = await env.KV.get('issue')
  if (issueKey !== new Date().toISOString().slice(0, 10)) return
  if (await env.KV.get('digest_enqueued') === issueKey) return

  const { results } = await env.DB.prepare(
    'SELECT id FROM subscribers WHERE last_sent_week IS NULL OR last_sent_week != ?'
  ).bind(issueKey).all()

  // sendBatch takes at most 100 messages.
  for (let i = 0; i < results.length; i += 100) {
    const messages = results.slice(i, i + 100).map(r => ({ body: { subscriberId: r.id, issueKey } }))
    await env.DIGEST_QUEUE.sendBatch(messages)
  }

  await env.KV.put('digest_enqueued', issueKey)
  console.log(`digest ${issueKey}: queued ${results.length} subscribers`)
}
