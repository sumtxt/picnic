---
title: "📦 Archive"
tagline: "Snapshots of Paper Picnic Editions."
layout: page
---

<ul class="list-group list-group mt-3">
{% for issue in site.data.archive_index %}
    <li class="list-group-item">
        <a href="{{ site.baseurl }}/archive/{{ issue.date }}/">
            {{ issue.date | date: "%B %-d, %Y" }}</a>
    </li>
{% endfor %}
</ul>
