// Which GitHub Actions workflow each Cloudflare cron starts. Every cron here
// must also be listed in wrangler.toml [triggers] crons (and vice versa).
// Days of the week are written as names: Cloudflare numbers them from 1 = Sunday,
// unlike standard cron.
export const CRON_JOBS = {
  '0 3 * * FRI': 'crawl.yml',
  '0 16 * * THU': 'subscriber-report.yml',
}
