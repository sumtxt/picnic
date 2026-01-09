const axios = require('axios');
const fs = require('fs');
const path = require('path');
const Mustache = require('mustache');
const { convert } = require('html-to-text');

// Configuration
const OUTPUT_DIR = '../output';
const PARAMETERS_DIR = '../parameters';
const RESEND_API_URL = 'https://api.resend.com/emails';

// Data sources
const PUBLICATIONS_FILE = path.join(OUTPUT_DIR, 'publications.json');
const JOURNALS_FILE = path.join(PARAMETERS_DIR, 'journals.json');

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
 * Build journal category map from journals.json
 */
function buildJournalCategoryMap(journalsData) {
  const categoryMap = {};
  journalsData.forEach(journal => {
    categoryMap[journal.id] = {
      category: journal.category,
      category_rank: journal.category_rank,
      name: journal.name
    };
  });
  return categoryMap;
}

/**
 * Filter and sort journals by category
 */
function filterJournalsByCategory(publications, journalMap, categoryName) {
  const filtered = publications.filter(pub => {
    const journalInfo = journalMap[pub.journal_id];
    return journalInfo && journalInfo.category === categoryName;
  });

  // Sort by category_rank
  filtered.sort((a, b) => {
    const rankA = journalMap[a.journal_id].category_rank;
    const rankB = journalMap[b.journal_id].category_rank;
    return rankA - rankB;
  });

  return filtered;
}

/**
 * Count articles and journals from filtered data
 */
function countArticles(journals) {
  if (!journals || journals.length === 0) {
    return [0, 0];
  }

  const journalCount = journals.length;
  const articleCount = journals.reduce((total, journal) => {
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

    // Load publications and journals data
    const publicationsData = await parseJson(PUBLICATIONS_FILE);
    const journalsData = await parseJson(JOURNALS_FILE);

    if (!publicationsData) {
      console.error('Failed to fetch publications data');
      process.exit(1);
    }

    if (!journalsData) {
      console.error('Failed to fetch journals data');
      process.exit(1);
    }

    // Check if there's an update today
    const today = getTodayDate();

    if (today !== publicationsData.update) {
      console.error('No update found for today');
      process.exit(1);
    }

    console.log('Update found for today, generating email...');

    // Build journal category map
    const journalMap = buildJournalCategoryMap(journalsData);

    // Filter and sort journals by category
    const polsciJournals = filterJournalsByCategory(publicationsData.content, journalMap, 'Political Science');
    const irJournals = filterJournalsByCategory(publicationsData.content, journalMap, 'International Relations');
    const paJournals = filterJournalsByCategory(publicationsData.content, journalMap, 'Public Administration');
    const ecoJournals = filterJournalsByCategory(publicationsData.content, journalMap, 'Economics');
    const socJournals = filterJournalsByCategory(publicationsData.content, journalMap, 'Sociology');
    const mulJournals = filterJournalsByCategory(publicationsData.content, journalMap, 'Multidisciplinary');

    // Prepare template data
    const templateData = {
      update: publicationsData.update,
      formatted_date: formatDate(publicationsData.update),
      polsci_n: countArticles(polsciJournals),
      ir_n: countArticles(irJournals),
      pa_n: countArticles(paJournals),
      eco_n: countArticles(ecoJournals),
      soc_n: countArticles(socJournals),
      mul_n: countArticles(mulJournals),
      polsci_content: polsciJournals.length > 0 ? { journals: polsciJournals } : null,
      ir_content: irJournals.length > 0 ? { journals: irJournals } : null,
      pa_content: paJournals.length > 0 ? { journals: paJournals } : null
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
