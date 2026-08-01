---
title: "Manage Email Preferences"
layout: page
permalink: /preferences
---

<div id="status-message" class="alert d-none mb-4" role="alert"></div>
<div id="loading-msg" class="text-muted">Loading your preferences…</div>

<div id="preferences-container" class="d-none">

  <p>Update which journals and preprint categories you receive weekly alerts for.</p>

  <form id="preferences-form">

    <hr class="my-4">
    <h2 class="h5 mb-3">Journals</h2>

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

    <div class="mt-4 d-flex gap-2">
      <button type="submit" class="btn btn-primary" id="save-btn">Save preferences</button>
      <button type="button" class="btn btn-outline-danger" id="unsubscribe-btn">Unsubscribe</button>
    </div>

  </form>
</div>

<script src="/assets/js/preferences.js"></script>
