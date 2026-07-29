---
title: "Paper Picnic Data"
layout: main
categories:
  - Political Science
  - International Relations
  - Public Administration
  - Economics
  - Sociology
  - Multidisciplinary
  - Communication Studies
  - Environmental Studies
  - Migration Studies
---

<div class="container my-5">
<p>The tables below show the number of retrieved articles without a filter tag for the last two months across all journals. For the complete (long-format) dataset covering all weeks since the launch on 23.08.2024, click here: <a href="./json/stats.csv">stats.csv</a></p>

{%- assign all_stats = site.data.stats -%}
{%- assign journals = site.data.journals -%}

{%- assign all_dates = all_stats | map: "crawl_date" | uniq | sort | reverse -%}
{%- assign recent_dates = all_dates | slice: 0, 8 -%}

<table class="table table-hover table-sm">
    <thead>
        <tr>
            <th></th>
            {%- for date in recent_dates -%}
            <th>{{ date | date: "%d. %b" }}</th>
            {%- endfor -%}
        </tr>
    </thead>
    <tbody>
        {%- for category in page.categories -%}
        {%- assign category_journals = journals | where: "category", category | sort: "category_rank" -%}
        <tr class="table-active">
            <td colspan="{{ recent_dates | size | plus: 1 }}"><strong>{{ category }}</strong></td>
        </tr>
        {%- for journal in category_journals -%}
        <tr>
            <td>{{ journal.name }}</td>
            {%- for date in recent_dates -%}
            {%- assign stat_entry = all_stats | where: "id", journal.id | where: "crawl_date", date | first -%}
            <td>{%- if stat_entry -%}{{ stat_entry.paper_count }}{%- endif -%}</td>
            {%- endfor -%}
        </tr>
        {%- endfor -%}
        <tr class="table-active">
            <td><strong>Total</strong></td>
            {%- for date in recent_dates -%}
            {%- assign date_total = 0 -%}
            {%- for journal in category_journals -%}
            {%- assign stat_entry = all_stats | where: "id", journal.id | where: "crawl_date", date | first -%}
            {%- if stat_entry -%}
            {%- assign date_total = date_total | plus: stat_entry.paper_count -%}
            {%- endif -%}
            {%- endfor -%}
            <td><strong>{{ date_total }}</strong></td>
            {%- endfor -%}
        </tr>
        <tr>
            <td colspan="{{ recent_dates | size | plus: 1 }}" style="height: 1rem;"></td>
        </tr>
        {%- endfor -%}
    </tbody>
</table>

</div>