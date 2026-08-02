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

Use the checkboxes below to select the journals and SocArXiv/OSF Preprints categories you want in your weekly email. Click the "Generate" button. Then send the generated text block to the displayed email address via your university email address. We'll reply to confirm your subscription.

<br>
<hr>

<div class="article-card">
<form id="subscribe-form">

<fieldset class="mb-3">
  <legend class="h5 mb-3">Content Selection</legend>
  <p class="text-muted small">Select the journals and preprint categories you want included.</p>

  {% include journal_select.html categories_list=page.journals %}
  </fieldset>

  <div class="mt-4">
    <button type="button" class="btn btn-primary" id="generate-btn">Generate</button>
  </div>

</form>
</div>

<div id="email-block-section" class="d-none mt-4">
  <p class="mb-2">Copy the text below and email it, unchanged, to <a href="mailto:subscribe@paper-picnic.com">subscribe@paper-picnic.com</a> from your university email address. The subject line doesn't matter. We'll reply to confirm.</p>
  <pre id="email-block" style="font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 1rem; border-radius: 4px; white-space: pre; overflow-x: auto; font-size: 0.9rem;"></pre>
  <button type="button" class="btn btn-primary btn-sm mt-2" id="copy-btn">Copy</button>
  <span id="copy-confirm" class="ms-2 text-success d-none">Copied!</span>
</div>

<div id="no-selection-hint" class="alert alert-info d-none mt-4" role="alert">
  Please select at least one journal or preprint category above before generating your subscription email.
</div>

<br>
<hr>


### FAQ ###

1. _Why are subscriptions limited to emails from universities?_ The technical infrastructure for this service comes with a cost covered by the maintainer. These costs grow with the number of subscribers. To control expenditures, university domains are used as a screening device to limit sign-ups. If you do not have a university email address, please use the <a href="{{ site.baseurl }}/notifications">Picnic Notifications</a> instead.

2. _Are you experimenting on me, train models on my data, or sell my data?_ No, never. Read more in the privacy policy. 

3. _How do I unsubscribe?_ Email _unsubscribe@paper-picnic.com_ (subject and body can just say "unsubscribe"), or use the List-Unsubscribe link in any of your weekly emails.

<script src="/assets/js/subscribe.js"></script>
