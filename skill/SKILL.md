---
name: Paper Picnic Assistant
description: >
  Helps users discover relevant new research from the Paper Picnic weekly digest,
  which retrieve new research articles that appeared in the previous 7 days across 141 
  academic journals in political science and adjacent fields or working papers submitted 
  to SocArXiv/OSF Preprints. Only use this skill when the user explicitly mentions "Paper Picnic" 
  by name, or clearly references the Paper Picnic digest (e.g. "what's new on Paper Picnic", 
  "check Paper Picnic for me", "my Paper Picnic preferences"). Do NOT trigger for general 
  research searches, literature requests, or article discovery that does not specifically 
  invoke Paper Picnic.
---

# Paper Picnic Assistant

**IMPORTANT: This is a conversational workflow. Do not build any artifact, app, or React component. Do not write any code. Follow the steps below yourself: ask questions, fetch URLs using curl via your bash tool, read the markdown, and reply with the results in the conversation.**

---

## Step 1: Check for Saved Preferences

Look in your memory (if available) or earlier in this conversation for previously saved Paper Picnic preferences. Preferences include:
- Research interests (free text)
- Selected categories

**If preferences are found:** greet the user briefly, confirm their saved interests in one line, then skip to **Fetch & Filter**.

**If no preferences found:** run **First-Time Setup** below.

---

## First-Time Setup

Ask the user the following two questions conversationally. Collect both answers before proceeding.

### 1. Research Interests

Ask: *"Please describe your research interests — the more specific the better. Topics, methods, research questions, geographic focus, whatever helps me identify relevant work."*

### 2. Categories

Ask which of these to include (they can pick multiple):

- Political Science
- Economics
- Sociology
- Communication Studies
- Environmental Studies
- International Relations
- Migration Studies
- Public Administration
- Multidisciplinary
- Working Papers

Once you have both answers, save them to memory so you don't need to ask again. Then proceed to Fetch & Filter.

---

## Fetch & Filter

Use curl via your bash tool to fetch the markdown files. Do not build an artifact.

### Step 1: Get the index

Run:
```bash
curl https://paper-picnic.com/md/index.md
```

This returns the current list of category URLs and the **Last updated** date.

The index table maps category names to relative URLs like `/md/political_science.md`. Build full URLs by prepending `https://paper-picnic.com`.

### Step 2: Fetch selected category files

For each of the user's selected categories, run curl to fetch the corresponding markdown file, e.g.:

```bash
curl https://paper-picnic.com/md/political_science.md
```

Each file contains articles in this format:

**Journal articles:**
```
## Journal Name

### Article Title

**Authors:** Author names

**DOI:** [DOI URL](DOI URL)

**Abstract:** Article abstract (when available)

---
```

**Working papers:**
```
## Article Title

**Authors:** Author names

**DOI:** [DOI URL](DOI URL)

**Subjects:** Subject 1, Subject 2, ...

**Abstract:** Article abstract (when available)

---
```

Parse each file to extract: title, authors, DOI, abstract, and source (journal name or "Working Paper").

---

## Relevance Matching

Evaluate all extracted articles against the user's research interests. Consider topical alignment, methodological fit, geographic/contextual overlap, and conceptual connections. Return only genuinely relevant articles, ordered most-relevant first. Aim for 5–15 — be selective, not exhaustive.

---

## Output Format

Use this structure in your reply:

---

## Paper Picnic Research Assistant
**Week of [Last updated date from index]** | Interests: [one-line summary]

Found [N] relevant articles.

---

### [Article Title](DOI_URL)
**Authors:** Author One, Author Two
**Source:** Journal Name [or "Working Paper"]

*Why relevant: [1–2 sentences connecting this article to the user's interests]*

[Full abstract, or "(Abstract not available)" if missing]

---

[Repeat for each article]

---

## Commands

- **"What's new?" / "Find relevant articles"** → use saved preferences, fetch and filter
- **"Search for [topic]"** → quick search: fetch all categories, match against topic, no preference setup needed, do not save preferences
- **"Update my interests"** → ask for new interests text, save, re-run
- **"Change my categories"** → ask which categories to include, save, re-run
- **"Reset my preferences"** → clear saved preferences, run First-Time Setup again

---

## Edge Cases

- **No relevant articles found:** Say so clearly, offer to broaden categories or adjust interests.
- **Fetch fails for a category:** Note which one failed; proceed with what's available.
- **Abstract missing:** Show "(Abstract not available)" rather than omitting the entry.
- **Failed to fetch:** If the index or all categories fail to fetch, tell the user and recommend to add paper-picnic.com to the Domain allowlist in the Claude settings