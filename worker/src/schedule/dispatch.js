// Starts a GitHub Actions workflow on main, unless it already ran today (UTC).
//
// Needs env.GITHUB_REPO ("owner/name", wrangler.toml [vars]) and the secret
// env.GH_DISPATCH_TOKEN (fine-grained PAT for this repo with "Actions: write").

export async function dispatchWorkflow(env, workflow) {
  const url = `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${workflow}`
  const headers = {
    'Authorization': `Bearer ${env.GH_DISPATCH_TOKEN}`,
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'paper-picnic-worker',
  }

  const today = new Date().toISOString().slice(0, 10)
  const runs = await fetch(`${url}/runs?created=%3E%3D${today}&per_page=1`, { headers })
  if (!runs.ok) throw new Error(`${workflow}: run lookup failed with HTTP ${runs.status}`)
  if ((await runs.json()).total_count > 0) {
    console.log(`${workflow}: already ran today, skipping`)
    return 'skipped'
  }

  const resp = await fetch(`${url}/dispatches`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ ref: 'main' }),
  })
  if (!resp.ok) throw new Error(`${workflow}: dispatch failed with HTTP ${resp.status}`)
  console.log(`${workflow}: dispatched`)
  return 'dispatched'
}
