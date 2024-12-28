---
title: "Data"
layout: main
---

<div class="container">
<p>The table below shows the number of retrieved articles without a filter tag for the last two months and across all journals. For the complete dataset covering all weeks since the launch on 2024-08-23, click here: <a href="./json/stats.csv">stats.csv</a></p>

{% assign table_rows = site.data.stats %}

<table class="table table-hover table-sm">
    {% for row in table_rows %}
        {% if forloop.first %}
            <tr>
                {% for pair in row offset:2 limit:9 %}
                    <th>
                        {{ pair[0] }}
                    </th>
                {% endfor %}
            </tr>
        {% endif %}

        {% tablerow pair in row offset:2 limit:9  %}
            {{ pair[1] }}
        {% endtablerow %}
    {% endfor %}
</table>
</div>