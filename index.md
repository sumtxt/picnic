---
title: "Home"
layout: home
---

# Motivation #

Available tools to keep up with newly published research are often frustrating. Email alerts from publishers clutter the email inbox, arrive at seemingly random intervals, and do not include abstracts. Publisher RSS feeds are similarly frustrating to use as available RSS readers are either clunky or come with expensive subscription models. Signing up to email alerts or finding the RSS feeds from a handful of publishers can easily take an entire afternoon. Twitter/X - uhm. 

[Moritz Marbach](https://www.moritz-marbach.com/) built Paper Picnic to keep up with newly published research in Political Science. It relies on three key ideas: 

1. Updates once a week at a known time.
2. Displays all new research on a single web page without clutter. 
3. No registration, no ads and no personal data collection.

All data comes from the Crossref API. [Crossref](https://www.crossref.org/community/) is the world’s largest registry of Digital Object Identifiers (DOIs) and metadata. Continuously updated by publishers, Crossref provides an easy way to get metadata for research articles.  

<br>
<hr>

# Backend #

The backend is a crawler written in R living in a GitHub repository. Every Friday, GitHub Actions executes the crawler. Once the crawler finishes, the crawled data is put in a JSON file and rendered into a HTML file using GitHub Pages. 

For each journal, the crawler retrieves all articles added to a journal in the previous week. To that end, it requests all articles for which the field "created" or "published" in the Crossref database is within the last seven days. 

The crawler retrieves title, authors, full-text link, and abstract. Unfortunately, not all publishers add abstracts. Examples include the publisher Elsevier or Taylor & Francis, which for all of their journals never include abstracts (see [this](https://www.crossref.org/blog/i4oa-hall-of-fame-2023-edition/) Crossref Blog for details). 

Since journals typically have two ISSN numbers (one for print and one for electronic, see [here](https://en.wikipedia.org/wiki/ISSN)), the crawler retrieves articles for both ISSN numbers and deduplicates the results. The ISSN numbers used for the crawler come from the Crossref lookup [tool](https://www.crossref.org/titleList/). 

Once an article has been crawled, its unique identifier (the DOI) is added to a list. This list is checked by the crawler at every runtime. Only articles that the crawler has not seen before are included in the data update. This ensures that articles appearing first online and then again in print are only included once on Paper Picnic.

When the title is generic, e.g., when it includes the word "Errata", "Frontmatter" or "Backmatter", the crawler adds a filter tag. For articles from multidisciplinary journals, the crawler prompts GPT-4o mini: "You are given content from a new issue of a multidisciplinary scientific journal. Respond 'Yes' if the content is a research article in any social science discipline and 'No' otherwise". All content that includes this filter tag is hidden in the default view but can be displayed by clicking on the +N button at the top left for every journal.

<br>

<hr>

# Contribute #

1. Find and fix bugs or add new features to the crawler/web page. GitHub repository: [github.com/sumtxt/paper-picnic](https://github.com/sumtxt/picnic).

2. Use the crawled data for your own tool: <button type="button" class="align-items-center btn btn-primary btn-sm rounded-pill" data-bs-toggle="modal" data-bs-target="#jsonlist">All JSON Files</button>

3. Build a better (and equally open source) version of this page. 

4. Support [The Initiative for Open Abstracts](https://i4oa.org/).

5. <script type="text/javascript" src="https://cdnjs.buymeacoffee.com/1.0.0/button.prod.min.js" data-name="bmc-button" data-slug="mmarbach" data-color="#FFDD00" data-emoji="☕"  data-font="Cookie" data-text="Buy me a coffee" data-outline-color="#000000" data-font-color="#000000" data-coffee-color="#ffffff" ></script>

