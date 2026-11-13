// Node loader hook: imports .mustache files as text, as wrangler's [[rules]] do.
import { readFile } from 'node:fs/promises'

export async function load(url, context, next) {
  if (!url.endsWith('.mustache')) return next(url, context)
  const text = await readFile(new URL(url), 'utf8')
  return { format: 'module', source: `export default ${JSON.stringify(text)}`, shortCircuit: true }
}
