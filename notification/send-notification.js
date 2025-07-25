const axios = require('axios');
const fs = require('fs');
const Mustache = require('mustache');

// Load environment variables for local testing
if (fs.existsSync('.env')) {
  require('dotenv').config();
}

// Configuration
const BASE_URL = 'https://paper-picnic.com/json';
const RESEND_API_URL = 'https://api.resend.com/emails';

// Data sources
const DATA_SOURCES = {
  politics: `${BASE_URL}/politics.json`,
  economics: `${BASE_URL}/economics.json`,
  sociology: `${BASE_URL}/sociology.json`,
  multidisciplinary: `${BASE_URL}/multidisciplinary.json`,
  public_administration_and_policy: `${BASE_URL}/public_administration_and_policy.json`,
  communication: `${BASE_URL}/communication.json`,
  migration: `${BASE_URL}/migration.json`,
  environmental_and_climate_politics_studies: `${BASE_URL}/environmental_and_climate_politics_studies.json`
};

/**
 * Fetch and parse JSON data from URL
 */
async function parseJson(url) {
  try {
    const response = await axios.get(url);
    return response.data;
  } catch (error) {
    console.error(`Error fetching data from ${url}:`, error.message);
    return null;
  }
}

/**
 * Count articles and journals from data
 */
function countArticles(data) {
  if (!data || !data.content) {
    return [0, 0];
  }
  
  const journalCount = data.content.length;
  const articleCount = data.content.reduce((total, journal) => {
    return total + (journal.articles ? journal.articles.length : 0);
  }, 0);
  
  return [journalCount, articleCount];
}

/**
 * Format date to readable string
 */
function formatDate(dateString) {
  const date = new Date(dateString);
  const options = { month: 'long', day: 'numeric', year: 'numeric' };
  return date.toLocaleDateString('en-US', options);
}

/**
 * Get today's date in YYYY-MM-DD format
 */
function getTodayDate() {
  const today = new Date();
  // Adjust for London timezone (UTC+1)
  const londonTime = new Date(today.getTime() + (1 * 60 * 60 * 1000));
  return londonTime.toISOString().split('T')[0];
}

/**
 * Generate HTML email content
 */
function generateEmailHtml(data) {
  const template = fs.readFileSync('email-template.html', 'utf8');
  return Mustache.render(template, data);
}

/**
 * Send email via Resend API
 */
async function sendEmail(subject, htmlBody, textBody = '') {
  const emailData = {
    from: process.env.RESEND_EMAIL_FROM,
    to: [process.env.RESEND_EMAIL_TO],
    subject: subject,
    html: htmlBody,
    text: textBody || 'Please view this email in HTML format.'
  };

  try {
    const response = await axios.post(RESEND_API_URL, emailData, {
      headers: {
        'Authorization': `Bearer ${process.env.RESEND_API_KEY}`,
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Email sent successfully:', response.data);
    return true;
  } catch (error) {
    console.error('Error sending email:', error.response?.data || error.message);
    return false;
  }
}

/**
 * Main function
 */
async function main() {
  try {
    console.log('Starting Paper Picnic notification process...');
    
    // Fetch main politics data to check for updates
    const politicsData = await parseJson(DATA_SOURCES.politics);
    
    if (!politicsData) {
      console.error('Failed to fetch politics data');
      await sendEmail(
        'Paper Picnic Notification: Error fetching data',
        '<p>There was an error fetching the latest data from Paper Picnic.</p>'
      );
      return;
    }

    // Check if there's an update today
    const today = getTodayDate();
    console.log(`Today's date: ${today}`);
    console.log(`Data update date: ${politicsData.update}`);
    
    if (today !== politicsData.update) {
      console.log('No update found for today');
      await sendEmail(
        'Paper Picnic Notification: No update found',
        '<p>No new papers were found for today\'s date.</p>'
      );
      return;
    }

    console.log('Update found for today, generating email...');

    // Fetch data for all categories
    const [economicsData, sociologyData, multidisciplinaryData] = await Promise.all([
      parseJson(DATA_SOURCES.economics),
      parseJson(DATA_SOURCES.sociology),
      parseJson(DATA_SOURCES.multidisciplinary)
    ]);

    // Prepare template data
    const templateData = {
      content: politicsData.content,
      update: politicsData.update,
      formatted_date: formatDate(politicsData.update),
      pol_n: countArticles(politicsData),
      eco_n: countArticles(economicsData),
      soc_n: countArticles(sociologyData),
      mul_n: countArticles(multidisciplinaryData)
    };

    // Generate email content
    const htmlBody = generateEmailHtml(templateData);
    const subject = `[Paper Picnic] New Baskets from ${templateData.formatted_date}`;

    // Send email
    const success = await sendEmail(subject, htmlBody);
    
    if (success) {
      console.log('Notification sent successfully!');
    } else {
      console.error('Failed to send notification');
      process.exit(1);
    }

  } catch (error) {
    console.error('Error in main process:', error);
    process.exit(1);
  }
}

// Run the main function
main();
