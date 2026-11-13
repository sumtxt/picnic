// Pure functions that turn the KV data (publications, preprints, journals,
// OSF subjects) into the per-subscriber sections rendered by digest.mustache.

const DISCIPLINE_ORDER = [
  'Political Science',
  'International Relations',
  'Public Administration',
  'Economics',
  'Sociology',
  'Multidisciplinary',
  'Communication Studies',
  'Environmental Studies',
  'Migration Studies',
]

export function formatDate(dateString) {
  return new Date(dateString + 'T12:00:00Z').toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  })
}

export function buildJournalMap(journalsData) {
  return Object.fromEntries(journalsData.map(j => [j.id, { category: j.category, category_rank: j.category_rank, name: j.name }]))
}

export function buildSubgroupMap(osfSubjects) {
  return Object.fromEntries((osfSubjects.subgroups || []).map(sg => [sg.id, sg.name]))
}

export function buildOsfIdToSubgroup(osfSubjects) {
  const map = {}
  for (const sg of osfSubjects.subgroups || []) {
    for (const osf of sg.osf || []) {
      map[osf.id] = sg.id
    }
  }
  return map
}

export function groupBySubscriber(rows, valueKey) {
  const map = {}
  for (const row of rows) {
    if (!map[row.subscriber_id]) map[row.subscriber_id] = []
    map[row.subscriber_id].push(row[valueKey])
  }
  return map
}

export function buildDisciplineSections(pubContent, journalMap, subscriberJournalIds) {
  const selected = new Set(subscriberJournalIds)
  const byCategory = {}
  for (const pub of pubContent) {
    const info = journalMap[pub.journal_id]
    if (!info || !selected.has(pub.journal_id)) continue
    if (!pub.articles || pub.articles.length === 0) continue
    if (!byCategory[info.category]) {
      byCategory[info.category] = { rank: info.category_rank, journals: [] }
    }
    byCategory[info.category].journals.push({
      journal_name: pub.journal_name,
      rank: info.category_rank,
      articles: pub.articles,
    })
  }
  return Object.entries(byCategory)
    .sort((a, b) => {
      const orderA = DISCIPLINE_ORDER.indexOf(a[0])
      const orderB = DISCIPLINE_ORDER.indexOf(b[0])
      if (orderA === -1 && orderB === -1) return a[0].localeCompare(b[0])
      if (orderA === -1) return 1
      if (orderB === -1) return -1
      return orderA - orderB
    })
    .map(([name, data]) => ({
      id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      name,
      journals: data.journals.sort((a, b) => a.rank - b.rank),
    }))
}

export function buildPreprintsSection(preprints, osfIdToSubgroup, subgroupMap, subscriberOsfCategories) {
  const articles = preprints?.content?.articles
  if (!articles || subscriberOsfCategories.length === 0) return null
  const selected = new Set(subscriberOsfCategories)
  const bySubgroup = {}
  for (const article of articles) {
    const subgroupIds = new Set((article.subjects || []).map(s => osfIdToSubgroup[s.id]).filter(Boolean))
    for (const sgId of subgroupIds) {
      if (!selected.has(sgId)) continue
      if (!bySubgroup[sgId]) bySubgroup[sgId] = []
      bySubgroup[sgId].push(article)
    }
  }
  const groups = Object.entries(bySubgroup).map(([id, items]) => ({ group_name: subgroupMap[id] || id, items }))
  return groups.length > 0 ? { groups } : null
}
