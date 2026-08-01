(function () {
  'use strict';

  var WORKER_URL = 'https://api.paper-picnic.com';

  function showStatus(message, type) {
    var el = document.getElementById('status-message');
    el.textContent = message;
    el.className = 'alert alert-' + type + ' mb-4';
  }

  // Handle status param from confirmation redirect
  var params = new URLSearchParams(window.location.search);
  var status = params.get('status');
  if (status === 'confirmed') {
    showStatus('Your subscription is confirmed! You will receive your first email on the next Friday after the weekly crawl.', 'success');
    var container = document.getElementById('subscribe-form-container');
    if (container) container.classList.add('d-none');
  } else if (status === 'already_confirmed') {
    showStatus('Your subscription was already confirmed.', 'info');
  }

  // Select-all buttons
  document.querySelectorAll('.select-all-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var cat = btn.getAttribute('data-category');
      var boxes = document.querySelectorAll('.cat-' + cat);
      var allChecked = Array.from(boxes).every(function (b) { return b.checked; });
      boxes.forEach(function (b) { b.checked = !allChecked; });
      btn.textContent = allChecked ? 'Select all' : 'Deselect all';
    });
  });

  var form = document.getElementById('subscribe-form');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    var email = document.getElementById('email-input').value.trim();
    var journals = Array.from(document.querySelectorAll('input[name="journal"]:checked'))
      .map(function (c) { return c.value; });
    var osf_categories = Array.from(document.querySelectorAll('input[name="osf_category"]:checked'))
      .map(function (c) { return c.value; });

    if (!email) { showStatus('Please enter your email address.', 'danger'); return; }
    if (journals.length === 0 && osf_categories.length === 0) {
      showStatus('Please select at least one journal or preprint category.', 'danger');
      return;
    }

    var btn = document.getElementById('submit-btn');
    var spinner = document.getElementById('submit-spinner');
    btn.disabled = true;
    spinner.classList.remove('d-none');

    fetch(WORKER_URL + '/api/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, journals: journals, osf_categories: osf_categories }),
    })
      .then(function (resp) { return resp.json().then(function (data) { return { ok: resp.ok, data: data }; }); })
      .then(function (result) {
        if (result.ok) {
          showStatus(result.data.message || 'Please check your email to confirm your subscription.', 'success');
          form.reset();
        } else {
          showStatus(result.data.error || 'Something went wrong. Please try again.', 'danger');
        }
      })
      .catch(function () {
        showStatus('Network error. Please try again.', 'danger');
      })
      .finally(function () {
        btn.disabled = false;
        spinner.classList.add('d-none');
      });
  });
})();
