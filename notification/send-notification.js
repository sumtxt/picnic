const axios = require('axios');
const fs = require('fs');
const path = require('path');
const Mustache = require('mustache');
const { convert } = require('html-to-text');

// Configuration
const OUTPUT_DIR = '../output';
const RESEND_API_URL = 'https://api.resend.com/emails';

// Data sources
const DATA_SOURCES = {
  politics: path.join(OUTPUT_DIR, 'politics.json'),
  economics: path.join(OUTPUT_DIR, 'economics.json'),
  sociology: path.join(OUTPUT_DIR, 'sociology.json'),
  multidisciplinary: path.join(OUTPUT_DIR, 'multidisciplinary.json'),
  public_administration_and_policy: path.join(OUTPUT_DIR, 'public_administration_and_policy.json'),
  communication: path.join(OUTPUT_DIR, 'communication.json'),
  migration: path.join(OUTPUT_DIR, 'migration.json'),
  environmental_and_climate_politics_studies: path.join(OUTPUT_DIR, 'environmental_and_climate_politics_studies.json')
};

/**
 * Read and parse JSON data from local file
 */
async function parseJson(filePath) {
  try {
    const fullPath = path.resolve(__dirname, filePath);
    if (!fs.existsSync(fullPath)) {
      console.error(`File not found: ${fullPath}`);
      return null;
    }
    const data = fs.readFileSync(fullPath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error(`Error reading data from ${filePath}:`, error.message);
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
  return today.toISOString().split('T')[0];
}

/**
 * Generate HTML email content
 */
function generateEmailHtml(data) {
  const template = fs.readFileSync('email-template.html', 'utf8');
  return Mustache.render(template, data);
}

/**
 * Convert HTML to plain text
 */
function generatePlainText(htmlBody) {
  const options = {
    wordwrap: 80
  };
  
  return convert(htmlBody, options);
}

/**
 * Send email via Resend API
 */
async function sendEmail(subject, htmlBody) {
  
  textBody = generatePlainText(htmlBody);

  const emailData = {
    from: process.env.RESEND_EMAIL_FROM,
    to: [process.env.RESEND_EMAIL_TO],
    subject: subject,
    html: htmlBody,
    text: textBody
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
      process.exit(1);
    }

    // Check if there's an update today
    const today = getTodayDate();
    
    //if (today !== politicsData.update) {
    //  console.error('No update found for today');
    //  process.exit(1);
    //}

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
