---
title: "👋 About"
tagline: "Paper Picnic is a tool to keep up with research in Political Science."
layout: page

journals:
  - category: Political Science
  - category: International Relations
    notes: "170 journals listed in JCR. Nominally top 5%: 8.5 journals. Seven of the top 9 overlap with Political Science top 70, so we add the two remaining journals (International Security, Foreign Affairs)."
  - category: Public Administration
    notes: "90 journals listed in JCR. Nominally top 5%: 4.5 journals. Three of the top 5 overlap with Political Science, so we add the two remaining journals (Journal of Policy Analysis and Management, Public Administration Review). We also include Climate Policy (ranked 6th) given its high rank in Environmental Studies."
  - category: Economics
    notes: "620 journals listed in JCR. Nominally top 5%: 31 journals. We add these journals but exclude six finance journals (Journal of Finance, Journal of Financial Economics, Review of Financial Studies, Journal of Accounting & Economics, Annual Review of Financial Economics, Review of Finance), four macroeconomics journals (NBER Macroeconomics Annual, American Economic Journal: Macroeconomics, Brookings Papers on Economic Activity, Journal of Monetary Economics), and one statistics journals (Journal of Business & Economic Statistics). We add two additional journals (rank 32-33): Economic Journal and AEJ: Microeconomics."
  - category: Sociology
    notes: "221 journals listed in JCR (Sociology) and 50 in Demography. Nominally top 5%: 11 journals from Sociology and 2.5 from Demography. We add the top Sociology journals, but exclude three special-interest journals (Gender & Society, Sociology of Education, Journal of Health and Social Behavior), and add European Sociological Review (official journal of the European Consortium for Sociological Research). We add the top 2 from Demography (Demography, Population and Development Review) and move the third (Comparative Migration Studies) to the Migration Studies baket."
  - category: Multidisciplinary
    notes: "137 journals listed in JCR. Nominally top 5%: 6.9 journals. We include the 7 highest-ranked journals whose aims and scope explicitly include social science research."
  - category: Communication Studies
    notes: "229 journals listed in JCR. Nominally top 5%: 11.5 journals. We include 12 journals, but excluding the Journal of Advertising."
  - category: Environmental Studies
    notes: "193 journals listed in JCR. Nominally top 5%: 9.7 journals. We include 10 journals."
  - category: Migration Studies
    notes: "No dedicated JCR category. We include the 7 journals with the highest h5-index in the Google Scholar Top Publications list under Human Migration, plus the Journal of Race, Ethnicity, and Politics (JREP), the official journal of APSA's Race, Ethnicity, and Politics section."
---

{%- assign count_total = site.data.journals | size -%}


### Overview ###

Keeping up with new research shouldn't mean drowning in email alerts. Paper Picnic is a free, open-source tool that aggregates new research papers from {{ count_total }} academic journals in political science (and adjacent fields) as well as working papers from SocArXiv and OSF Preprints.

The tool is built around three principles:

1. Updates once a week at a known time. Every Friday morning UTC, the site refreshes with papers published in the previous two weeks.
2. Displays everything on a single page without clutter. Browse all new papers in a clean, customizable, ad-free interface.
3. No registration, no ads, no tracking. Access the site immediately without handing over your email address or personal data.

<br>

### Journal Selection ###

We curate journals using the [Journal Citation Reports (JCR)](https://jcr.clarivate.com/jcr/home) and their Article Influence Score (AIS) metric (2024 edition, including both the Social Science Citation Index and the Emerging Sources Citation Index). Unlike the more popular Journal Impact Factor (JIF), which treats all citations equally, the AIS weights citations by the influence of the citing journal and discounts self-citations. For more information see [this](https://paperpicnic.substack.com/publish/post/183794092) Substack post. 

**Political Science** forms the core. JCR lists 325 journals in this category, and we include the top 70—approximately the top 20% when ranked by AIS. We also added PS: Political Science & Politics, an official journal of the American Political Science Association, despite its lower ranking.

**Adjacent fields** are seeded by journals that are listed in Political Science and at least one adjacent field (e.g., International Organization is listed in both Political Science and International Relations). We complement these journals with the top journals from each adjacent field, using a threshold of approximately the top 5% by AIS. 

The result: a curated collection of journals that captures the most influential research across Political Science and in adjacent fields. For a list of included journals by field of research and some notes on deviations from the top 5% threshold, click below. 

{% include journal_list.html categories_list=page.journals %}

<br>

### How the Crawl Works ###

Every Friday at 2 AM UTC, we automatically retrieve newly published papers across all {{ count_total }} journals. The data comes from the [Crossref](https://www.crossref.org/community/) API, the world's largest registry of Digital Object Identifiers (DOIs) and metadata. Publishers continuously update Crossref, making it a reliable source for paper metadata.

**The retrieval process:** We query Crossref for papers published in the previous 14 days using each journal's ISSN and eISSN. The 14-day window (rather than 7) ensures we don't miss papers that were published late in the previous week but not yet indexed by Crossref during the last crawl. We maintain a list of previously seen DOIs to filter out duplicates, so each paper appears only once.

**What we retrieve:** For each paper, we collect the title, authors, abstract, and a link to the full text. Unfortunately, not all publishers include abstracts in their Crossref metadata. Major publishers like Elsevier and Taylor & Francis don't provide abstracts for any of their journals. (Learn more from [The Initiative for Open Abstracts](https://i4oa.org/).)

**Filtering non-relevant content:** For multidisciplinary journals like Science or Nature, we use GPT-4o mini to identify social science content. Non-relevant papers are hidden by default but remain accessible via the "+N" button. We also filter generic content like errata to reduce clutter.

<br>

### Working Papers from OSF ###

Beyond journal articles, we include working papers from two Open Science Framework (OSF) repositories: [SocArXiv](https://osf.io/preprints/socarxiv) and [OSF Preprints](https://osf.io/preprints/). Every week, we collect papers that authors classified under "Social and Behavioral Sciences" and added to a repository in the previous 14 days. 

As with journal articles, the 14-day window helps catch papers that were posted late in the previous week. We maintain a list of previously retrieved working paper IDs to filter out revisions—if a paper appeared in an earlier edition, we don't show it again when the authors post an updated version.

**What we retrieve:** In addition to title, authors, abstract, and link, we also collect the subject tags that authors provide. Not all authors tag their papers, so some working papers appear without subject classifications but are still included in the working paper basket.

**Why not SSRN?** Many authors still post working papers to SSRN, and we'd have liked to include them. Unfortunately, SSRN's Terms of Use (which is owned by Elsevier) prohibit reformatting, reposting, or redisplaying "a significant part of the SSRN eLibrary." This restriction prevents us from incorporating SSRN papers into Paper Picnic.

<br>

### Open Source & Data Access ###

Paper Picnic is open source, and all code is available in the [GitHub Repository](https://github.com/sumtxt/picnic). We welcome contributions—whether you want to fix bugs, add features, improve the crawler, or enhance the web interface. All data from the weekly crawl is available as machine-readable JSON files if you want to build your own tool on top of it:  

 <ul class="list-group list-group mt-3">
{% for file in site.static_files %}
{% if file.extname == ".json" -%}
<li class="list-group-item"><a href="{{ site.baseurl }}{{ file.path }}">{{ file.path }}</a></li>
{%- endif %}
{% endfor %}
</ul>

{% include coffee_button.html %}