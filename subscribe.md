---
title: "Subscribe to Personalized Alerts"
layout: page
permalink: /subscribe
---

<div id="status-message" class="alert d-none mb-4" role="alert"></div>

<div id="subscribe-form-container">

<p>Select exactly which journals and preprint categories you want to receive weekly email alerts for.
Only <strong>university email addresses</strong> are accepted.</p>

<form id="subscribe-form">

  <div class="mb-3">
    <label for="email-input" class="form-label fw-semibold">University email address</label>
    <input type="email" class="form-control" id="email-input" placeholder="name@university.edu" required>
  </div>

  <hr class="my-4">
  <h2 class="h5 mb-3">Journals</h2>
  <p class="text-muted small">Select the journals you want included in your weekly alert. Use "Select all" to pick an entire discipline at once.</p>

  {% assign grouped = site.data.journals | group_by: 'category' | sort: 'name' %}
  {% for group in grouped %}
  <div class="mb-4">
    <div class="d-flex align-items-center mb-2">
      <h3 class="h6 mb-0 me-3">{{ group.name }}</h3>
      <button type="button" class="btn btn-sm btn-outline-secondary py-0 select-all-btn"
              data-category="{{ group.name | slugify }}">Select all</button>
    </div>
    {% assign sorted = group.items | sort: 'category_rank' %}
    {% for journal in sorted %}
    <div class="form-check ms-2">
      <input class="form-check-input journal-check cat-{{ group.name | slugify }}"
             type="checkbox" name="journal" value="{{ journal.id }}"
             id="j-{{ journal.id }}">
      <label class="form-check-label" for="j-{{ journal.id }}">{{ journal.name }}</label>
    </div>
    {% endfor %}
  </div>
  {% endfor %}

  <hr class="my-4">
  <h2 class="h5 mb-3">Preprints (SocArXiv / OSF)</h2>
  <p class="text-muted small">Select preprint subject categories to include SocArXiv preprints in your alert.</p>

  {% assign subgroups = site.data.osf_subjects.subgroups %}
  {% for sg in subgroups %}
  {% unless sg.id == 'ooo' or sg.id == 'xxx' %}
  <div class="form-check ms-2">
    <input class="form-check-input" type="checkbox" name="osf_category"
           value="{{ sg.id }}" id="osf-{{ sg.id }}">
    <label class="form-check-label" for="osf-{{ sg.id }}">{{ sg.name }}</label>
  </div>
  {% endunless %}
  {% endfor %}

  <div class="mt-4">
    <button type="submit" class="btn btn-primary" id="submit-btn">Subscribe</button>
    <span id="submit-spinner" class="ms-2 d-none">Sending…</span>
  </div>

</form>
</div>

<script src="/assets/js/subscribe.js"></script>
