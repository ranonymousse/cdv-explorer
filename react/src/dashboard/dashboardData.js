import * as d3 from 'd3';
import { CLASSIFICATION_DIMENSIONS } from './constants';

const WORD_CLOUD_STOPWORDS = new Set([
  'code', 'tt', '0', '1', '2', '3', '4', '32', 'x',
  'key', 'not', 'if', 'can', 'pre', 'must', 'which', 's',
  'https', 'com', 'should', 'may', 'have', 'new', 'any', 'no',
  'using', 'use', 'only', 'used', 'all', 'we', 'they', 'when',
  'each', 'time', 'i', 'but', 'would', 'than', 'same', 'm',
  'their', 'more', 'also', 'such', 'there', 'then', 'these',
  'bit', 'bytes', 'byte', 'message', 'comments', 'data', 'value',
  'type', 'size', 'set', 'path', 'ref', 'org', 'p', 'n',
  'github', 'mediawiki', 'sub', 'script', 'public', 'one', 'number', 'keys', 'other', 'first',
  'following', 'implementation', 'string', 'case', 'node', 'private',
  'master', 'does', 'specification', 'two', 'change',
  'valid', 'where', 'after', 'return', 'e', 'g', 'without', 'standard',
  'user', 'order', 't', 'index', 'b', 'example', 'nodes', 'non', 'style',
  'format', 'bits', 'so', 'license', 'some', 'field', 'length',
  'messages', 'defined', 'being', 'uri', 'created', 'k', 'required',
  'possible', 'both', 'see', 'let', 'however', 'list', 'wiki', 'into', 'based',
  'them', 'blob', 'stack', 'sup', 'been', 'name', 'c', 'do', 'r', '5', '8', 'up', 'make', 'since', 'given', 'per', 'while',
]);

function cleanAuthorName(author) {
  return String(author || '').split('<')[0].trim();
}

export function normalizeProposalFilterValue(value) {
  const text = String(value || '').trim();
  if (!text) {
    return '';
  }

  const match = text.match(/^(?:bip\s*[- ]*)?0*(\d+)$/i);
  return match ? match[1] : text;
}

function normalizeChordLayer(value) {
  const text = String(value || '').trim();
  if (!text || text.includes('Unknown')) {
    return 'Unspecified';
  }
  return text;
}

function normalizeChordStatus(value) {
  const text = String(value || '').trim() || 'Unknown Status';
  const base = text.split('(')[0].trim() || 'Unknown Status';
  return base.includes('Unknown') ? 'Unknown Status' : base;
}

function normalizeChordType(value) {
  const text = String(value || '').trim() || 'Unknown Type';
  const aliases = {
    Standard: 'Standards Track',
    Standards: 'Standards Track',
    'Standard Track': 'Standards Track',
    'Standards-Track': 'Standards Track',
  };
  const normalized = aliases[text] || text;
  return normalized.includes('Unknown') ? 'Unknown Type' : normalized;
}

export function parseProposalFilterExpression(text, availableProposalIds = []) {
  const availableSet = new Set((availableProposalIds || []).map(normalizeProposalFilterValue));
  const selected = new Set();

  String(text || '')
    .split(',')
    .map((token) => token.trim())
    .filter(Boolean)
    .forEach((token) => {
      const rangeMatch = token.match(/^(?:bip\s*[- ]*)?0*(\d+)\s*-\s*(?:bip\s*[- ]*)?0*(\d+)$/i);

      if (rangeMatch) {
        const start = Number(rangeMatch[1]);
        const end = Number(rangeMatch[2]);
        const lower = Math.min(start, end);
        const upper = Math.max(start, end);

        for (let value = lower; value <= upper; value += 1) {
          const normalized = String(value);
          if (availableSet.has(normalized)) {
            selected.add(normalized);
          }
        }
        return;
      }

      const normalized = normalizeProposalFilterValue(token);
      if (availableSet.has(normalized)) {
        selected.add(normalized);
      }
    });

  return Array.from(selected).sort((left, right) => Number(left) - Number(right));
}

function computeWeightedEigenvectorCentrality(nodeIds, adjacency, maxIterations = 1000, tolerance = 1e-6) {
  const authorIds = Array.from(new Set((nodeIds || []).map((id) => String(id))));
  const nodeCount = authorIds.length;

  if (nodeCount === 0) {
    return new Map();
  }

  const values = new Map(authorIds.map((id) => [id, 1 / Math.sqrt(nodeCount)]));

  for (let iteration = 0; iteration < maxIterations; iteration += 1) {
    const nextValues = new Map(authorIds.map((id) => [id, 0]));

    authorIds.forEach((id) => {
      const neighbors = adjacency.get(id) || [];
      neighbors.forEach(({ id: neighborId, weight }) => {
        nextValues.set(id, nextValues.get(id) + Number(weight || 0) * (values.get(neighborId) || 0));
      });
    });

    const norm = Math.sqrt(
      Array.from(nextValues.values()).reduce((sum, value) => sum + value ** 2, 0)
    );

    if (norm === 0) {
      return new Map(authorIds.map((id) => [id, 0]));
    }

    let delta = 0;
    authorIds.forEach((id) => {
      const normalizedValue = nextValues.get(id) / norm;
      delta += Math.abs(normalizedValue - (values.get(id) || 0));
      values.set(id, normalizedValue);
    });

    if (delta < nodeCount * tolerance) {
      break;
    }
  }

  return values;
}

function buildDisplayCollaborationComponents(nodeIds, adjacency) {
  const isolatedIds = [];
  const visited = new Set();
  const components = [];

  nodeIds.forEach((id) => {
    const neighbors = adjacency.get(id) || [];
    if (neighbors.length === 0) {
      isolatedIds.push(id);
      return;
    }

    if (visited.has(id)) {
      return;
    }

    const queue = [id];
    const members = [];
    visited.add(id);

    while (queue.length > 0) {
      const current = queue.shift();
      members.push(current);

      (adjacency.get(current) || []).forEach(({ id: neighborId }) => {
        if (visited.has(neighborId)) {
          return;
        }
        visited.add(neighborId);
        queue.push(neighborId);
      });
    }

    components.push(members);
  });

  components.sort((left, right) => right.length - left.length);

  if (isolatedIds.length > 0) {
    components.push(isolatedIds.sort((left, right) => left.localeCompare(right)));
  }

  return components;
}

function buildCollaborationDerivedData(collaborationNetwork, collaborationCentrality, topAuthorSet = new Set()) {
  const rawNodes = collaborationNetwork?.nodes || [];
  const rawEdges = collaborationNetwork?.edges || [];
  const nodeIds = rawNodes.map((node) => String(node.id)).filter(Boolean);
  const adjacency = new Map(nodeIds.map((id) => [id, []]));
  const weightedDegreeByAuthor = new Map(nodeIds.map((id) => [id, 0]));

  rawEdges.forEach((edge) => {
    const source = String(edge.source);
    const target = String(edge.target);
    const weight = Number(edge.weight || 1);

    if (!adjacency.has(source)) {
      adjacency.set(source, []);
      weightedDegreeByAuthor.set(source, 0);
    }
    if (!adjacency.has(target)) {
      adjacency.set(target, []);
      weightedDegreeByAuthor.set(target, 0);
    }

    adjacency.get(source).push({ id: target, weight });
    adjacency.get(target).push({ id: source, weight });
    weightedDegreeByAuthor.set(source, (weightedDegreeByAuthor.get(source) || 0) + weight);
    weightedDegreeByAuthor.set(target, (weightedDegreeByAuthor.get(target) || 0) + weight);
  });

  const components = buildDisplayCollaborationComponents(nodeIds, adjacency);

  const clusterMetaByAuthor = new Map();
  components.forEach((members, index) => {
    members.forEach((author) => {
      clusterMetaByAuthor.set(author, {
        clusterId: index + 1,
        clusterSize: members.length,
      });
    });
  });

  const centralityByAuthor = new Map(
    (collaborationCentrality || []).map((entry) => [String(entry.author), entry])
  );
  const weightedEigenvectorByAuthor = computeWeightedEigenvectorCentrality(nodeIds, adjacency);

  const degreeRows = rawNodes
    .map((node) => {
      const author = String(node.id);
      const clusterMeta = clusterMetaByAuthor.get(author) || { clusterId: null, clusterSize: 1 };
      const centrality = centralityByAuthor.get(author) || {};

      return {
        author,
        clusterId: clusterMeta.clusterId,
        clusterSize: clusterMeta.clusterSize,
        rawDegree: Number((adjacency.get(author) || []).length),
        weightedDegree: Number(weightedDegreeByAuthor.get(author) || 0),
        normalizedDegree: Number(centrality.degree || 0),
      };
    })
    .sort((left, right) => {
      if (right.rawDegree !== left.rawDegree) {
        return right.rawDegree - left.rawDegree;
      }
      return left.author.localeCompare(right.author);
    });

  const eigenvectorRows = nodeIds
    .map((author) => {
      const clusterMeta = clusterMetaByAuthor.get(author) || { clusterId: null, clusterSize: 1 };
      const centrality = centralityByAuthor.get(author) || {};

      return {
        author,
        clusterId: clusterMeta.clusterId,
        clusterSize: clusterMeta.clusterSize,
        eigenvector: Number(centrality.eigenvector || 0),
        weightedEigenvector: Number(weightedEigenvectorByAuthor.get(author) || 0),
      };
    })
    .sort((left, right) => {
      if (right.eigenvector !== left.eigenvector) {
        return right.eigenvector - left.eigenvector;
      }
      return left.author.localeCompare(right.author);
    });

  const eigenvectorByAuthor = new Map(
    eigenvectorRows.map((row) => [row.author, row])
  );
  const metricsRows = degreeRows.map((row) => {
    const eigenvectorRow = eigenvectorByAuthor.get(row.author) || {};

    return {
      ...row,
      displayAuthor: topAuthorSet.has(row.author) ? `${row.author}*` : row.author,
      eigenvector: Number(eigenvectorRow.eigenvector || 0),
      weightedEigenvector: Number(eigenvectorRow.weightedEigenvector || 0),
    };
  });
  const nodeCount = nodeIds.length;
  const edgeCount = rawEdges.length;
  const isolatedAuthorCount = degreeRows.filter((row) => Number(row.rawDegree || 0) === 0).length;
  const clusterCount = components.length;
  const density = nodeCount > 1 ? edgeCount / ((nodeCount * (nodeCount - 1)) / 2) : 0;

  return {
    summary: {
      nodeCount,
      edgeCount,
      isolatedAuthorCount,
      clusterCount,
      density,
    },
    metricsRows,
  };
}

function normalizeCategoryValue(value) {
  const text = String(value || '').trim();
  return text || 'Unspecified';
}

function buildFacetDistribution(nodes, field) {
  const counts = new Map();
  const bipsByCategory = new Map();

  (nodes || []).forEach((node) => {
    const category = normalizeCategoryValue(node?.[field]);
    counts.set(category, (counts.get(category) || 0) + 1);

    if (node?.id != null) {
      if (!bipsByCategory.has(category)) {
        bipsByCategory.set(category, new Set());
      }
      bipsByCategory.get(category).add(String(node.id));
    }
  });

  return Array.from(counts.entries())
    .map(([id, value]) => ({
      id,
      value,
      bips: Array.from(bipsByCategory.get(id) || []).sort((left, right) => Number(left) - Number(right)),
    }))
    .sort((left, right) => right.value - left.value || left.id.localeCompare(right.id));
}

function buildFacetTimeline(nodes, field) {
  const countsByYear = new Map();
  const bipsByYear = new Map();
  const allCategories = new Set();

  (nodes || []).forEach((node) => {
    if (!node?.created) {
      return;
    }

    const year = new Date(node.created).getFullYear();
    if (!Number.isFinite(year) || year <= 1900) {
      return;
    }

    const category = normalizeCategoryValue(node?.[field]);
    allCategories.add(category);
    const bipId = node?.id != null ? String(node.id) : null;

    if (!countsByYear.has(year)) {
      countsByYear.set(year, new Map());
    }
    if (!bipsByYear.has(year)) {
      bipsByYear.set(year, new Map());
    }

    const yearMap = countsByYear.get(year);
    yearMap.set(category, (yearMap.get(category) || 0) + 1);

    if (bipId) {
      const yearBipsMap = bipsByYear.get(year);
      if (!yearBipsMap.has(category)) {
        yearBipsMap.set(category, new Set());
      }
      yearBipsMap.get(category).add(bipId);
    }
  });

  const categories = Array.from(allCategories).sort((left, right) => left.localeCompare(right));
  const rows = Array.from(countsByYear.entries())
    .sort((left, right) => left[0] - right[0])
    .map(([year, categoryMap]) => {
      const values = {};
      const bips = {};
      const yearBipsMap = bipsByYear.get(year) || new Map();
      categories.forEach((category) => {
        values[category] = categoryMap.get(category) || 0;
        bips[category] = Array.from(yearBipsMap.get(category) || []).sort(
          (left, right) => Number(left) - Number(right)
        );
      });

      return {
        year: String(year),
        values,
        bips,
      };
    });

  return {
    categories,
    rows,
  };
}

export function buildWordCloudData(nodes, selectedProposalIds = []) {
  const selectedSet = new Set(
    (selectedProposalIds || []).map(normalizeProposalFilterValue).filter(Boolean)
  );
  const wordCounts = {};

  (nodes || []).forEach((node) => {
    const proposalId = normalizeProposalFilterValue(node?.id);
    if (selectedSet.size > 0 && !selectedSet.has(proposalId)) {
      return;
    }

    const wordList = node?.word_list;
    if (!wordList) {
      return;
    }

    Object.entries(wordList).forEach(([word, count]) => {
      wordCounts[word] = (wordCounts[word] || 0) + count;
    });
  });

  return Object.entries(wordCounts)
    .filter(([word]) => !WORD_CLOUD_STOPWORDS.has(word.toLowerCase()))
    .map(([word, count]) => ({ word, count }))
    .sort((left, right) => right.count - left.count)
    .slice(0, 100);
}

function buildClassificationChordData(nodes, categoryDomains = {}) {
  const groups = [];
  const groupIndexByKey = new Map();
  const pairCounts = new Map();
  const pairBips = new Map();

  CLASSIFICATION_DIMENSIONS.forEach(({ field, label }) => {
    const categories = Array.isArray(categoryDomains[field]) ? categoryDomains[field] : [];
    categories.forEach((category) => {
      const key = `${field}|||${category}`;
      groupIndexByKey.set(key, groups.length);
      groups.push({
        id: key,
        label: `${label}: ${category}`,
        dimension: field,
        category,
      });
    });
  });

  (nodes || []).forEach((node) => {
    const bipId = node?.id != null ? String(node.id) : null;
    const values = {
      layer: normalizeChordLayer(node?.layer),
      status: normalizeChordStatus(node?.status),
      type: normalizeChordType(node?.type),
    };

    [
      ['layer', 'status'],
      ['layer', 'type'],
      ['status', 'type'],
    ].forEach(([leftField, rightField]) => {
      const leftKey = `${leftField}|||${values[leftField]}`;
      const rightKey = `${rightField}|||${values[rightField]}`;
      const leftIndex = groupIndexByKey.get(leftKey);
      const rightIndex = groupIndexByKey.get(rightKey);

      if (leftIndex == null || rightIndex == null) {
        return;
      }

      const pairKey = [leftIndex, rightIndex].sort((left, right) => left - right).join('|||');
      pairCounts.set(pairKey, (pairCounts.get(pairKey) || 0) + 1);

      if (bipId) {
        if (!pairBips.has(pairKey)) {
          pairBips.set(pairKey, new Set());
        }
        pairBips.get(pairKey).add(bipId);
      }
    });
  });

  const matrix = Array.from({ length: groups.length }, () => Array(groups.length).fill(0));
  pairCounts.forEach((count, key) => {
    const [leftIndex, rightIndex] = key.split('|||').map(Number);
    matrix[leftIndex][rightIndex] = count;
    matrix[rightIndex][leftIndex] = count;
  });

  return {
    groups,
    matrix,
    pairBips: Object.fromEntries(
      Array.from(pairBips.entries()).map(([key, bipSet]) => [
        key,
        Array.from(bipSet).sort((left, right) => Number(left) - Number(right)),
      ])
    ),
  };
}

export function buildDashboardData(dataset) {
  const authorship = dataset.authorship || {};
  const dependencyMetrics = dataset.dependencyMetrics || { by_approach: {} };
  const conformity = dataset.conformity || {};
  const authorBipsByAuthor = new Map();
  const bipsByYear = new Map();

  dataset.nodes.forEach((node) => {
    const bipId = node?.id != null ? String(node.id) : null;
    if (!bipId) {
      return;
    }

    const authors = Array.isArray(node.author)
      ? node.author.map(cleanAuthorName).filter(Boolean)
      : [];

    authors.forEach((author) => {
      if (!authorBipsByAuthor.has(author)) {
        authorBipsByAuthor.set(author, new Set());
      }
      authorBipsByAuthor.get(author).add(bipId);
    });

    if (node?.created) {
      const year = new Date(node.created).getFullYear();
      if (Number.isFinite(year) && year > 1900) {
        if (!bipsByYear.has(year)) {
          bipsByYear.set(year, new Set());
        }
        bipsByYear.get(year).add(bipId);
      }
    }
  });

  const yearData = (authorship.bips_per_year || []).length
    ? (authorship.bips_per_year || []).map((entry) => ({
      ...entry,
      bips: Array.from(bipsByYear.get(Number(entry.year)) || []).sort((left, right) => Number(left) - Number(right)),
    }))
    : Array.from(
      d3.rollup(
        dataset.nodes.filter((node) => {
          if (!node?.created) {
            return false;
          }
          const year = new Date(node.created).getFullYear();
          return Number.isFinite(year) && year > 1900;
        }),
        (values) => values.length,
        (node) => new Date(node.created).getFullYear()
      ),
      ([year, count]) => ({
        year,
        count,
        bips: Array.from(bipsByYear.get(Number(year)) || []).sort((left, right) => Number(left) - Number(right)),
      })
    ).sort((a, b) => a.year - b.year);

  const wordCloudData = buildWordCloudData(dataset.nodes);
  const conformityRows = (conformity.per_proposal || [])
    .filter((entry) => (
      Number.isFinite(Number(entry?.bip2_score)) || Number.isFinite(Number(entry?.bip3_score))
    ))
    .map((entry) => ({
      ...entry,
      id: String(entry.id),
    }))
    .sort((left, right) => Number(left.id) - Number(right.id));

  const buildFailedChecksSeries = (standardKey) => {
    const failuresByCheck = new Map();

    conformityRows.forEach((entry) => {
      const checks = Array.isArray(entry?.compliance?.[standardKey]?.checks)
        ? entry.compliance[standardKey].checks
        : [];

      checks
        .filter((check) => check?.passed === false)
        .forEach((check) => {
          const id = String(check?.id || check?.label || 'unknown-check');
          const label = String(check?.label || check?.id || 'Unnamed check').trim();

          if (!failuresByCheck.has(id)) {
            failuresByCheck.set(id, {
              id,
              label,
              count: 0,
              proposals: new Set(),
            });
          }

          const current = failuresByCheck.get(id);
          current.count += 1;
          current.proposals.add(String(entry.id));
        });
    });

    return Array.from(failuresByCheck.values())
      .map((entry) => ({
        ...entry,
        proposals: Array.from(entry.proposals).sort((left, right) => Number(left) - Number(right)),
      }))
      .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label))
      .slice(0, 10);
  };

  const classificationDistributions = {
    layer: buildFacetDistribution(dataset.nodes, 'layer'),
    type: buildFacetDistribution(dataset.nodes, 'type'),
    status: buildFacetDistribution(dataset.nodes, 'status'),
  };
  const classificationTimeline = {
    layer: buildFacetTimeline(dataset.nodes, 'layer'),
    type: buildFacetTimeline(dataset.nodes, 'type'),
    status: buildFacetTimeline(dataset.nodes, 'status'),
  };
  const classificationCategoryDomains = Object.fromEntries(
    CLASSIFICATION_DIMENSIONS.map(({ field }) => [
      field,
      [
        ...classificationDistributions[field].map((entry) => entry.id),
        ...classificationTimeline[field].categories.filter(
          (category) => !classificationDistributions[field].some((entry) => entry.id === category)
        ),
      ],
    ])
  );

  const topAuthors = (authorship.top_authors || []).map((entry) => ({
    ...entry,
    bips: Array.from(authorBipsByAuthor.get(entry.author) || []).sort((left, right) => Number(left) - Number(right)),
  }));
  const topCollaborationAuthors = new Set(
    Array.from(authorBipsByAuthor.entries())
      .sort((left, right) => {
        const bipCountDifference = right[1].size - left[1].size;
        if (bipCountDifference !== 0) {
          return bipCountDifference;
        }
        return left[0].localeCompare(right[0]);
      })
      .slice(0, 10)
      .map(([author]) => author)
  );

  const sharedBipsByAuthorPair = new Map();
  dataset.nodes.forEach((node) => {
    const authors = Array.isArray(node.author)
      ? node.author.map(cleanAuthorName).filter(Boolean)
      : [];
    const uniqueAuthors = Array.from(new Set(authors));

    if (!node.id || uniqueAuthors.length < 2) {
      return;
    }

    for (let i = 0; i < uniqueAuthors.length; i += 1) {
      for (let j = i + 1; j < uniqueAuthors.length; j += 1) {
        const pairKey = [uniqueAuthors[i], uniqueAuthors[j]].sort().join('|||');
        if (!sharedBipsByAuthorPair.has(pairKey)) {
          sharedBipsByAuthorPair.set(pairKey, new Set());
        }
        sharedBipsByAuthorPair.get(pairKey).add(String(node.id));
      }
    }
  });

  const rawCollaborationNetwork = authorship.collaboration_network || { nodes: [], edges: [] };
  const rawCollaborationNodeIds = new Set(
    (rawCollaborationNetwork.nodes || []).map((node) => String(node.id)).filter(Boolean)
  );
  const collaborationNetwork = {
    ...rawCollaborationNetwork,
    nodes: [
      ...(rawCollaborationNetwork.nodes || []).map((node) => ({
        ...node,
        bips: Array.from(authorBipsByAuthor.get(node.id) || []).sort((left, right) => Number(left) - Number(right)),
      })),
      ...Array.from(authorBipsByAuthor.entries())
        .filter(([author]) => !rawCollaborationNodeIds.has(author))
        .map(([author, bipSet]) => ({
          id: author,
          degree: 0,
          bips: Array.from(bipSet).sort((left, right) => Number(left) - Number(right)),
        })),
    ],
    edges: (rawCollaborationNetwork.edges || []).map((edge) => {
      const pairKey = [edge.source, edge.target].sort().join('|||');
      const bips = Array.from(sharedBipsByAuthorPair.get(pairKey) || [])
        .sort((left, right) => Number(left) - Number(right));

      return {
        ...edge,
        bips,
      };
    }),
  };

  const {
    summary: collaborationMetricsSummary,
    metricsRows: collaborationMetricsRows,
  } = buildCollaborationDerivedData(
    collaborationNetwork,
    authorship.collaboration_centrality || [],
    topCollaborationAuthors,
  );

  return {
    yearData,
    wordCloudData,
    conformityRows,
    conformityFailedChecks: {
      bip2: buildFailedChecksSeries('bip2'),
      bip3: buildFailedChecksSeries('bip3'),
    },
    classificationDistributions,
    classificationTimeline,
    classificationCategoryDomains,
    classificationChordData: buildClassificationChordData(dataset.nodes, classificationCategoryDomains),
    topAuthors,
    authorContributionHistogram: authorship.author_contribution_histogram || [],
    collaborationNetwork,
    collaborationMetricsSummary,
    collaborationMetricsRows,
    dependencyMetrics,
  };
}
