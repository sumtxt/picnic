(function () {
  'use strict';

  var WORKER_URL = 'https://api.paper-picnic.com';

  var token = new URLSearchParams(window.location.search).get('token');
  var loadingEl = document.getElementById('loading-msg');
  var container = document.getElementById('preferences-container');
  var statusEl = document.getElementById('status-message');

  function showStatus(message, type) {
    statusEl.textContent = message;
    statusEl.className = 'alert alert-' + type + ' mb-4';
  }

  if (!token) {
    loadingEl.textContent = 'No token found. Please use the link from your weekly email to manage your preferences.';
    return;
  }

  // Load current preferences
  fetch(WORKER_URL + '/api/preferences?token=' + encodeURIComponent(token))
    .then(function (resp) {
      if (!resp.ok) throw new Error('Invalid or expired token.');
      return resp.json();
    })
    .then(function (prefs) {
      // Pre-check saved journals
      var journalSet = new Set(prefs.journals || []);
      document.querySelectorAll('input[name="journal"]').forEach(function (cb) {
        cb.checked = journalSet.has(cb.value);
      });

      // Pre-check saved OSF categories
      var osfSet = new Set(prefs.osf_categories || []);
      document.querySelectorAll('input[name="osf_category"]').forEach(function (cb) {
        cb.checked = osfSet.has(cb.value);
      });

      loadingEl.classList.add('d-none');
      container.classList.remove('d-none');
    })
    .catch(function (err) {
      loadingEl.textContent = err.message || 'Could not load preferences. Please use the link from your weekly email.';
    });

  // Save preferences
  var form = document.getElementById('preferences-form');
  form.addEventListener('submit', function (e) {
    e.preventDefault();

    var journals = Array.from(document.querySelectorAll('input[name="journal"]:checked'))
      .map(function (c) { return c.value; });
    var osf_categories = Array.from(document.querySelectorAll('input[name="osf_category"]:checked'))
      .map(function (c) { return c.value; });

    if (journals.length === 0 && osf_categories.length === 0) {
      showStatus('Please select at least one journal or preprint category before saving.', 'danger');
      return;
    }

    var btn = document.getElementById('save-btn');
    btn.disabled = true;
    btn.textContent = 'Saving…';

    fetch(WORKER_URL + '/api/preferences?token=' + encodeURIComponent(token), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ journals: journals, osf_categories: osf_categories }),
    })
      .then(function (resp) { return resp.json().then(function (d) { return { ok: resp.ok, data: d }; }); })
      .then(function (result) {
        if (result.ok) {
          showStatus('Preferences saved.', 'success');
        } else {
          showStatus(result.data.error || 'Could not save preferences.', 'danger');
        }
      })
      .catch(function () { showStatus('Network error. Please try again.', 'danger'); })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = 'Save preferences';
      });
  });

  // Unsubscribe
  document.getElementById('unsubscribe-btn').addEventListener('click', function () {
    if (!confirm('Are you sure you want to unsubscribe? All your data will be deleted.')) return;

    fetch(WORKER_URL + '/api/unsubscribe?token=' + encodeURIComponent(token), { method: 'DELETE' })
      .then(function (resp) { return resp.json(); })
      .then(function () {
        container.classList.add('d-none');
        showStatus('You have been unsubscribed. All your data has been deleted.', 'success');
      })
      .catch(function () { showStatus('Network error. Please try again.', 'danger'); });
  });
})();
