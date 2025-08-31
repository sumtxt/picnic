const SUPABASE_URL = 'https://yhunwflirlgpkqzetjtx.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlodW53ZmxpcmxncGtxemV0anR4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY1ODE2MTUsImV4cCI6MjA3MjE1NzYxNX0.kw59AL6Reu-kgHR5yTeh2bHozRWqxsXoeeqH_B6KCYI';

// Initialize Supabase client
const { createClient } = supabase;
const supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Auth state management
let currentUser = null;
let userJournalPreferences = new Set();

// Initialize authentication
async function initAuth() {
    // Get initial session
    const { data: { session } } = await supabaseClient.auth.getSession();
    
    if (session) {
        currentUser = session.user;
        await applyJournalVisibility();
        updateUIForLoggedInUser();
    } else {
        updateUIForLoggedOutUser();
    }

    // Listen for auth changes
    supabaseClient.auth.onAuthStateChange(async (event, session) => {
        console.log('Auth state change:', event);
        
        if (event === 'SIGNED_IN' && session) {
            currentUser = session.user;
            await applyJournalVisibility();
            updateUIForLoggedInUser();
        } else if (event === 'SIGNED_OUT') {
            currentUser = null;
            userJournalPreferences.clear();
            updateUIForLoggedOutUser();
        }
    });
}


// Send magic link for authentication
async function sendMagicLink(email) {
    try {
        const { error } = await supabaseClient.auth.signInWithOtp({
            email: email,
            options: {
                emailRedirectTo: window.location.origin
            }
        });

        if (error) throw error;
        
        return { success: true };
    } catch (error) {
        console.error('Error sending magic link:', error);
        return { success: false, error: error.message };
    }
}

// Sign out
async function signOut() {
    try {
        const { error } = await supabaseClient.auth.signOut();
        if (error) throw error;
    } catch (error) {
        console.error('Error signing out:', error);
    }
}

// Update journal UI state using jQuery and Bootstrap collapse
function setJournalVisibility(journalShort, isHidden) {
    const $button = $(`[data-journal="${journalShort}"]`);
    const $articles = $(`#main-articles-${journalShort}`);
    
    if (isHidden) {
        $articles.collapse('hide');
        $button.text('Show').removeClass('btn-outline-secondary').addClass('btn-outline-success');
    } else {
        $articles.collapse('show');
        $button.text('Hide').removeClass('btn-outline-success').addClass('btn-outline-secondary');
    }
}

// Toggle journal visibility
async function toggleJournalVisibility(journalShort) {
    if (!currentUser) {
        alert('Please log in to hide/unhide journals');
        return;
    }

    const isCurrentlyHidden = $(`[data-journal="${journalShort}"]`).text() === 'Show';

    try {
        if (isCurrentlyHidden) {
            await supabaseClient
                .from('journal_preferences')
                .delete()
                .eq('user_id', currentUser.id)
                .eq('journal_short', journalShort);
            
            setJournalVisibility(journalShort, false);
        } else {
            await supabaseClient
                .from('journal_preferences')
                .insert({
                    user_id: currentUser.id,
                    journal_short: journalShort,
                    is_hidden: true
                });
            
            setJournalVisibility(journalShort, true);
        }
    } catch (error) {
        console.error('Error updating journal preference:', error);
        alert('Error updating preference. Please try again.');
    }
}

// Apply saved preferences on page load
async function applyJournalVisibility() {
    if (!currentUser) return;

    try {
        const { data, error } = await supabaseClient
            .from('journal_preferences')
            .select('journal_short')
            .eq('user_id', currentUser.id)
            .eq('is_hidden', true);

        if (error) throw error;

        data.forEach(pref => setJournalVisibility(pref.journal_short, true));
    } catch (error) {
        console.error('Error loading preferences:', error);
    }
}

// Update UI for logged in user
function updateUIForLoggedInUser() {
    $('#login-section').hide();
    $('#user-section').show();
    $('#user-email').text(currentUser.email);
    $('.journal-toggle-btn').show();
}

// Update UI for logged out user
function updateUIForLoggedOutUser() {
    $('#login-section').show();
    $('#user-section').hide();
    $('.journal-toggle-btn').hide();
    $('[id^="main-articles-"]').collapse('show');
}

// Handle login form submission
async function handleLogin() {
    const email = $('#loginEmail').val();
    
    if (!email) {
        showLoginMessage('Please enter your email address.', 'danger');
        return;
    }

    const result = await sendMagicLink(email);
    
    if (result.success) {
        showLoginMessage('Magic link sent! Check your email and click the link to login.', 'success');
        $('#loginForm')[0].reset();
    } else {
        showLoginMessage(`Error: ${result.error}`, 'danger');
    }
}

// Show login message
function showLoginMessage(message, type) {
    $('#loginMessage').html(`<div class="alert alert-${type}" role="alert">${message}</div>`).show();
}

// Initialize when DOM is loaded
$(document).ready(initAuth);