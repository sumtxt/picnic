---
title: "Your Picnic Basket 📨"
layout: page
tagline: Subscribe to receive an automated weekly email with the articles from all your favourite journals and preprints submitted to OSF. Sign-ups are limited to university email addresses.
permalink: /subscribe
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


<div class="article-card">
<form id="subscribe-form">

<fieldset class="mb-3">
  <legend class="h5 mb-3">Content Selection</legend>
  <p class="text-muted small">Select the journals and preprint categories you want included.</p>

  {% include journal_select.html categories_list=page.journals %}
  </fieldset>

  <div id="status-message" class="alert d-none mb-4" role="alert"></div>

  <div class="mb-3">
    <label for="email-input" class="form-label fw-semibold">Email Address<p class="text-muted small">Only university email addresses are accepted.</p></label>
    <input type="email" class="form-control" id="email-input" placeholder="name@university.edu" required>
  </div>
  
  <div class="mt-4">
    <button type="submit" class="btn btn-primary" id="submit-btn">Subscribe</button>
    <span id="submit-spinner" class="ms-2 d-none">Sending…</span>
  </div>

</form>
</div>

<br>
<hr>

### FAQ ###

1. _Why are subscriptions limited to emails from universities?_ The technical infrastructure for this service comes with a cost covered by the maintainer. These costs grow with the number of subscribers. To control expenditures, university domains are used as a screening device to limit sign-ups. If you do not have a university email address, please use the <a href="/notifications">Picnic Notifications</a> instead.

2. _Are you experimenting on me, train models on my data, or sell my data?_ No, never. Read more in the privacy policy. 


<script src="/assets/js/subscribe.js"></script>
