// Which GitHub Actions workflow each Cloudflare cron starts. Every cron here
// must also be listed in wrangler.toml [triggers] crons (and vice versa).
export const CRON_JOBS = {
  '0 3 * * 5': 'crawl.yml',
  '0 16 * * 4': 'subscriber-report.yml',
}
