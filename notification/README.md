# Paper Picnic Email Notifications

This directory contains the GitHub Action workflow and scripts to send automated email notifications for Paper Picnic research updates, replacing the previous Google Apps Script implementation.

## Overview

The notification system:
1. Runs daily at 9 AM UTC (10 AM London time) via GitHub Actions
2. Fetches data from Paper Picnic JSON endpoints
3. Checks if there are updates for the current date
4. Generates and sends HTML email notifications using the Resend API
5. Only sends emails when new content is available

## Files

- `notification.yml` - GitHub Actions workflow configuration
- `send-notification.js` - Main Node.js script that handles data fetching and email sending
- `email-template.html` - Mustache template for generating HTML emails
- `code.gs` - Original Google Apps Script code (for reference)
- `Template.html` - Original Google Apps Script template (for reference)

## Setup

### 1. GitHub Secrets

Configure the following secrets in your GitHub repository settings:

- `RESEND_API_KEY` - Your Resend API key
- `RESEND_EMAIL_FROM` - Sender email address (must be verified in Resend)
- `RESEND_EMAIL_TO` - Recipient email address

### 2. Resend Account Setup

1. Sign up for a [Resend](https://resend.com) account
2. Verify your sending domain
3. Generate an API key
4. Add the API key to your GitHub secrets

### 3. Local Testing

To test the script locally without sending emails:

1. Navigate to the notification directory:
   ```bash
   cd notification
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Test email template generation (no email sending):
   ```bash
   npm test
   ```
   This will:
   - Fetch data from Paper Picnic APIs
   - Generate the HTML email
   - Save it as `test-email-output.html` for preview
   - Show article counts and environment status

4. For full testing with actual email sending:
   - Copy `.env.example` to `.env`
   - Fill in your Resend API credentials
   - Run: `npm start`

### 4. GitHub Actions Testing

You can manually trigger the workflow:
1. Go to the Actions tab in your GitHub repository
2. Select "Paper Picnic Email Notification"
3. Click "Run workflow"

## Key Differences from Google Apps Script

### Advantages of GitHub Actions approach:
- **Version Control**: All code is tracked in Git
- **Transparency**: Workflow runs are logged and visible
- **Flexibility**: Easy to modify scheduling and add new features
- **Cost**: GitHub Actions provides generous free tier
- **Integration**: Can easily integrate with other GitHub workflows

### Technical Changes:
- **Templating**: Switched from Google Apps Script HTML templates to Mustache.js
- **HTTP Requests**: Using Axios instead of UrlFetchApp
- **Email Service**: Using Resend API instead of Gmail/MailApp
- **Date Handling**: Explicit timezone handling for London time
- **Error Handling**: More robust error handling and logging

## Workflow Schedule

The workflow runs:
- Daily at 9 AM UTC (10 AM London time)
- Can be manually triggered via workflow_dispatch

## Email Template

The HTML email template includes:
- Summary of new papers by category (Politics, Economics, Sociology, Multidisciplinary)
- Full listing of political science papers with abstracts
- Links to other categories
- Unsubscribe information
- Responsive design with proper styling

## Monitoring

Check the GitHub Actions logs to monitor:
- Successful email sends
- Data fetching issues
- Template rendering problems
- API errors

## Troubleshooting

### Common Issues:

1. **No email received**: Check GitHub Actions logs for errors
2. **Template rendering issues**: Verify JSON data structure matches template expectations
3. **Resend API errors**: Ensure API key is valid and sender domain is verified
4. **Timezone issues**: The script accounts for London time (UTC+1)

### Debug Steps:

1. Check the Actions tab for workflow run logs
2. Verify all secrets are properly configured
3. Test Resend API key independently
4. Validate JSON endpoints are accessible

## Future Enhancements

Potential improvements:
- Add support for multiple recipients
- Implement email templates for different categories
- Add metrics tracking
- Support for different notification frequencies
- Integration with other communication channels (Slack, Discord, etc.)
