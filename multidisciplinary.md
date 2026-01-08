---
title: "Multidisciplinary"
layout: main
---
{%- assign data_journals = site.data.journals | where: "category", "Multidisciplinary" -%}
{%- assign data_crawl = "" | split: "" -%}
{%- for journal in data_journals -%}
  {%- for item in site.data.publications.content -%}
    {%- if item.journal_id == journal.id -%}
      {%- assign data_crawl = data_crawl | push: item -%}
      {%- break -%}
    {%- endif -%}
  {%- endfor -%}
{%- endfor -%}
{% include cards.html %}
