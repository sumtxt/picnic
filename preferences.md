---
title: "Manage Your Picnic Basket 📨"
layout: page
tagline: Update which journals and preprints you receive in your weekly email.
permalink: /preferences
journals:
  - category: Political Science
  - category: International Relations
  - category: Public Administration
  - category: Economics
  - category: Sociology
  - category: Multidisciplinary
  - category: Communication Studies
  - category: Environmental Studies
  - category: Migration Studies
---

<div id="loading-msg" class="text-muted">Loading your preferences…</div>

<div id="status-message" class="alert d-none mb-4" role="alert"></div>

<div id="preferences-container" class="article-card d-none">
<form id="preferences-form">

<fieldset class="mb-3">
  <legend class="h5 mb-3">Content Selection</legend>
  <p class="text-muted small">Select the journals and preprint categories you want included.</p>

  {% include journal_select.html categories_list=page.journals %}
  </fieldset>

  <div class="mt-4 d-flex gap-2">
    <button type="submit" class="btn btn-primary" id="save-btn">Save preferences</button>
    <button type="button" class="btn btn-outline-danger" id="unsubscribe-btn">Unsubscribe</button>
  </div>

</form>
</div>

<script src="/assets/js/preferences.js"></script>
