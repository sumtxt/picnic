// Plunk (transactional email provider): sending the digest and removing contacts
// on unsubscribe. Both need env.PLUNK_SECRET_KEY.

export async function sendPlunkEmail(to, subject, body, env, { reply, headers, subscriberId } = {}) {
  const resp = await fetch('https://next-api.useplunk.com/v1/send', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.PLUNK_SECRET_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      to,
      from: 'noreply@paper-picnic.com',
      subject,
      body,
      subscribed: false,
      ...(reply && { reply }),
      ...(headers && { headers }),
    }),
  })
  if (!resp.ok) {
    console.error('Plunk send failed:', resp.status, resp.statusText, `subscriber=${subscriberId ?? 'unknown'}`)
  }
  return resp.ok
}

export async function deletePlunkContact(email, env) {
  const listResp = await fetch(`https://next-api.useplunk.com/contacts?search=${encodeURIComponent(email)}`, {
    headers: { 'Authorization': `Bearer ${env.PLUNK_SECRET_KEY}` },
  })
  if (!listResp.ok) {
    console.error('Plunk contact lookup failed:', listResp.status, listResp.statusText)
    return
  }

  const { data } = await listResp.json()
  const contact = (data ?? []).find(c => c.email?.toLowerCase() === email.toLowerCase())
  if (!contact) return

  const delResp = await fetch(`https://next-api.useplunk.com/contacts/${contact.id}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${env.PLUNK_SECRET_KEY}` },
  })
  if (!delResp.ok) {
    console.error('Plunk contact delete failed:', delResp.status, delResp.statusText)
  }
}
