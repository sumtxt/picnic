const axios = require('axios');
const fs = require('fs');
const Mustache = require('mustache');

// Load environment variables for local testing
if (fs.existsSync('.env')) {
  require('dotenv').config();
}

// Configuration
const BASE_URL = 'https://paper-picnic.com/json';

// Data sources
const DATA_SOURCES = {
  politics: `${BASE_URL}/politics.json`,
  economics: `${BASE_URL}/economics.json`,
  sociology: `${BASE_URL}/sociology.json`,
  multidisciplinary: `${BASE_URL}/multidisciplinary.json`
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
 * Generate HTML email content
 */
function generateEmailHtml(data) {
  const template = fs.readFileSync('email-template.html', 'utf8');
  return Mustache.render(template, data);
}

/**
 * Test function - generates email HTML and saves to file
 */
async function testEmailGeneration() {
  try {
    console.log('Testing email generation...');
    
    // Fetch main politics data
    const politicsData = await parseJson(DATA_SOURCES.politics);
    
    if (!politicsData) {
      console.error('Failed to fetch politics data');
      return;
    }

    console.log(`Data update date: ${politicsData.update}`);
    console.log(`Found ${politicsData.content?.length || 0} journals`);

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

    console.log('Article counts:');
    console.log(`- Politics: ${templateData.pol_n[1]} articles in ${templateData.pol_n[0]} journals`);
    console.log(`- Economics: ${templateData.eco_n[1]} articles in ${templateData.eco_n[0]} journals`);
    console.log(`- Sociology: ${templateData.soc_n[1]} articles in ${templateData.soc_n[0]} journals`);
    console.log(`- Multidisciplinary: ${templateData.mul_n[1]} articles in ${templateData.mul_n[0]} journals`);

    // Generate email content
    const htmlBody = generateEmailHtml(templateData);
    const subject = `[Paper Picnic] New Baskets from ${templateData.formatted_date}`;

    // Save HTML to file for preview
    fs.writeFileSync('test-email-output.html', htmlBody);
    
    console.log('\n✅ Email generation test completed successfully!');
    console.log(`📧 Subject: ${subject}`);
    console.log('📄 HTML output saved to: test-email-output.html');
    console.log('🌐 Open test-email-output.html in your browser to preview the email');

    // Check environment variables
    console.log('\n🔧 Environment check:');
    console.log(`RESEND_API_KEY: ${process.env.RESEND_API_KEY ? '✅ Set' : '❌ Missing'}`);
    console.log(`RESEND_EMAIL_FROM: ${process.env.RESEND_EMAIL_FROM ? '✅ Set' : '❌ Missing'}`);
    console.log(`RESEND_EMAIL_TO: ${process.env.RESEND_EMAIL_TO ? '✅ Set' : '❌ Missing'}`);

    if (process.env.RESEND_API_KEY && process.env.RESEND_EMAIL_FROM && process.env.RESEND_EMAIL_TO) {
      console.log('\n🚀 All environment variables are set. You can run the full script with: npm start');
    } else {
      console.log('\n⚠️  Set up your .env file to test actual email sending');
    }

  } catch (error) {
    console.error('❌ Error in test:', error);
  }
}

// Run the test
testEmailGeneration();
