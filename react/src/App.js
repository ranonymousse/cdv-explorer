import { useEffect, useMemo, useRef, useState } from 'react';
import Navbar from './Navbar';
import { LINK_TYPE_OPTIONS, NetworkDiagram } from './NetworkDiagram';
import { ProposalTimelineChart } from './ProposalTimelineChart';
import { TopAuthorsChart } from './TopAuthorsChart';
import { AuthorContributionHistogram } from './AuthorContributionHistogram';
import { AuthorCollaborationNetwork } from './AuthorCollaborationNetwork';
import { AuthorCentralityTable } from './AuthorCentralityTable';
import { ProposalGraphMetricsTable } from './ProposalGraphMetricsTable';
import { DependencyComparisonHeatmaps } from './DependencyComparisonHeatmaps';
import { ClassificationPieChart } from './ClassificationPieChart';
import { ClassificationStackedTimelineChart } from './ClassificationStackedTimelineChart';
import { ClassificationChordDiagram } from './ClassificationChordDiagram';
import { FormalConformitySwarmPlot } from './FormalConformitySwarmPlot';
import { ConformityFailedChecksHistogram } from './ConformityFailedChecksHistogram';
import { WordCloud } from './WordCloud';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Tag } from 'primereact/tag';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { RadioButton } from 'primereact/radiobutton';
import './App.scss';
import * as d3 from 'd3';
import { HashRouter as Router, Routes, Route, useNavigate, useParams, Link } from 'react-router-dom';
import { ecosystems, ecosystemsById } from './ecosystems';
import { getAvailableSnapshots, getDatasetForSelection } from './data';
import { ThemeProvider, useTheme } from './theme';

const COLLABORATION_LAYOUT_OPTIONS = [
  { label: 'Balanced', value: 'balanced' },
  { label: 'Clustered', value: 'clustered' },
  { label: 'Spread', value: 'spread' },
];

const CLASSIFICATION_DIMENSIONS = [
  { field: 'layer', label: 'Layer' },
  { field: 'type', label: 'Type' },
  { field: 'status', label: 'Status' },
];

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
  'them', 'blob', 'stack', 'sup', 'been', 'name', 'c', 'do', 'r', '5', '8', 'up', 'make', 'since', 'given', 'per', 'while'
]);

function cleanAuthorName(author) {
  return String(author || '').split('<')[0].trim();
}

function getSourceRepositoryHref(repository) {
  const text = String(repository || '').trim();
  const githubMatch = text.match(/^github\/([^/]+)\/([^/]+)$/i);

  if (githubMatch) {
    return `https://github.com/${githubMatch[1]}/${githubMatch[2]}`;
  }

  return null;
}

function normalizeProposalFilterValue(value) {
  const text = String(value || '').trim();
  if (!text) {
    return '';
  }

  const match = text.match(/^(?:bip\s*[- ]*)?0*(\d+)$/i);
  return match ? match[1] : text;
}

function normalizeChordLayer(value) {
  const text = String(value || '').trim() || 'Unknown Layer';
  return text.includes('Unknown') ? 'Other' : text;
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

function parseProposalFilterExpression(text, availableProposalIds = []) {
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

function buildCollaborationDerivedData(collaborationNetwork, collaborationCentrality) {
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

  const visited = new Set();
  const components = [];
  nodeIds.forEach((id) => {
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
        rawDegree: Number(node.degree || 0),
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
      eigenvector: Number(eigenvectorRow.eigenvector || 0),
      weightedEigenvector: Number(eigenvectorRow.weightedEigenvector || 0),
    };
  });

  return {
    degreeRows,
    eigenvectorRows,
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

function buildWordCloudData(nodes, selectedProposalIds = []) {
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
  const groupKeys = [];
  const groups = [];
  const groupIndexByKey = new Map();
  const pairCounts = new Map();
  const pairBips = new Map();

  CLASSIFICATION_DIMENSIONS.forEach(({ field, label }) => {
    const categories = Array.isArray(categoryDomains[field]) ? categoryDomains[field] : [];
    categories.forEach((category) => {
      const key = `${field}|||${category}`;
      groupIndexByKey.set(key, groups.length);
      groupKeys.push(key);
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

    const pairs = [
      ['layer', 'status'],
      ['layer', 'type'],
      ['status', 'type'],
    ];

    pairs.forEach(([leftField, rightField]) => {
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

function buildDashboardData(dataset) {
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
  const conformityFailedChecks = {
    bip2: buildFailedChecksSeries('bip2'),
    bip3: buildFailedChecksSeries('bip3'),
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
  const classificationChordData = buildClassificationChordData(dataset.nodes, classificationCategoryDomains);

  const topAuthors = (authorship.top_authors || []).map((entry) => ({
    ...entry,
    bips: Array.from(authorBipsByAuthor.get(entry.author) || []).sort((left, right) => Number(left) - Number(right)),
  }));
  const authorContributionHistogram = authorship.author_contribution_histogram || [];
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
  const collaborationNetwork = {
    ...rawCollaborationNetwork,
    nodes: (rawCollaborationNetwork.nodes || []).map((node) => ({
      ...node,
      bips: Array.from(authorBipsByAuthor.get(node.id) || []).sort((left, right) => Number(left) - Number(right)),
    })),
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
  const collaborationCentrality = authorship.collaboration_centrality || [];
  const {
    metricsRows: collaborationMetricsRows,
  } = buildCollaborationDerivedData(collaborationNetwork, collaborationCentrality);

  return {
    yearData,
    wordCloudData,
    conformityRows,
    conformityFailedChecks,
    classificationDistributions,
    classificationTimeline,
    classificationCategoryDomains,
    classificationChordData,
    topAuthors,
    authorContributionHistogram,
    collaborationNetwork,
    collaborationCentrality,
    collaborationMetricsRows,
    dependencyMetrics,
  };
}

function sanitizeExportFileName(value) {
  return String(value || 'chart')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'chart';
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function ExportableCard({
  children,
  className = '',
  style,
  exportTitle = 'Chart',
  exportFileName = '',
}) {
  const cardRef = useRef(null);

  const handleExportPdf = () => {
    const sourceCard = cardRef.current;
    if (!sourceCard || typeof window === 'undefined') {
      return;
    }

    const exportTarget = sourceCard.querySelector('[data-export-target="true"]')
      || sourceCard.querySelector('svg[role="img"]')
      || sourceCard.querySelector('svg')
      || sourceCard;
    const exportRect = exportTarget.getBoundingClientRect();
    const viewBox = exportTarget.tagName.toLowerCase() === 'svg'
      ? exportTarget.getAttribute('viewBox')
      : null;
    const viewBoxParts = viewBox ? viewBox.split(/\s+/).map(Number) : [];
    const exportWidthPx = Math.max(
      320,
      Math.round(exportRect.width || exportTarget.clientWidth || viewBoxParts[2] || 800)
    );
    const exportHeightPx = Math.max(
      220,
      Math.round(exportRect.height || exportTarget.clientHeight || viewBoxParts[3] || 500)
    );
    const exportWidthPt = Math.round(exportWidthPx * 0.75);
    const exportHeightPt = Math.round(exportHeightPx * 0.75);

    const printWindow = window.open('', '_blank', 'width=1440,height=1024');
    if (!printWindow) {
      return;
    }

    const clonedTarget = exportTarget.cloneNode(true);
    clonedTarget.querySelectorAll('[data-export-control="true"]').forEach((node) => node.remove());
    const rootStyles = window.getComputedStyle(document.documentElement);
    const resolvedMarkup = clonedTarget.outerHTML.replace(/var\((--[^),\s]+)(?:,[^)]+)?\)/g, (_, variableName) => {
      const value = rootStyles.getPropertyValue(variableName).trim();
      return value || '#000000';
    });

    const styleMarkup = Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'))
      .map((node) => node.outerHTML)
      .join('\n');
    const theme = document.documentElement.dataset.theme || 'light';
    const themeMode = document.documentElement.dataset.themeMode || theme;
    const documentTitle = exportFileName || sanitizeExportFileName(exportTitle);

    printWindow.document.open();
    printWindow.document.write(`
      <!doctype html>
      <html data-theme="${escapeHtml(theme)}" data-theme-mode="${escapeHtml(themeMode)}">
        <head>
          <meta charset="utf-8" />
          <title>${escapeHtml(documentTitle)}</title>
          ${styleMarkup}
          <style>
            body {
              margin: 0;
              background: #ffffff;
            }

            .export-print-shell {
              width: ${exportWidthPx}px;
              margin: 0 auto;
            }

            [data-export-control="true"] {
              display: none !important;
            }

            .export-print-shell > svg {
              display: block;
              width: ${exportWidthPx}px;
              height: ${exportHeightPx}px;
            }

            @page {
              size: ${exportWidthPt}pt ${exportHeightPt}pt;
              margin: 0;
            }
          </style>
        </head>
        <body>
          <div class="export-print-shell">${resolvedMarkup}</div>
        </body>
      </html>
    `);
    printWindow.document.close();

    const triggerPrint = () => {
      printWindow.focus();
      printWindow.print();
    };

    printWindow.addEventListener('afterprint', () => {
      printWindow.close();
    }, { once: true });

    printWindow.addEventListener('load', () => {
      window.setTimeout(triggerPrint, 250);
    }, { once: true });
  };

  return (
    <div ref={cardRef} className={className} style={style}>
      <Card className="exportable-card">
        <div className="exportable-card__actions" data-export-control="true">
          <Button
            type="button"
            label="PDF"
            icon="pi pi-file-pdf"
            severity="secondary"
            text
            size="small"
            onClick={handleExportPdf}
          />
        </div>
        {children}
      </Card>
    </div>
  );
}

function EcosystemLanding() {
  const navigate = useNavigate();

  return (
    <section className="content">
      <h1>Community-Driven Variability Ecosystem Explorer</h1>
      <p>
        Modern decentralized software ecosystems evolve through crowdsourced improvement proposals (IPs) that are continuously shaped and autonomously implemented by independent actors. As a result, these ecosystems exhibit so-called Community-Driven
Variability (CDV), a novel paradigm that extends beyond traditional variability-intensive systems. This page allows to explore IPs of such ecosystems by providing interactive visualizations and insights about their evolution, authorship, classification, conformity, and inter-proposal relationships.
      </p>

      <div className="ecosystem-grid">
        {ecosystems.map((ecosystem) => {
          const available = ecosystem.status === 'available';

          return (
            <Card
              key={ecosystem.id}
              className={`ecosystem-card${available ? '' : ' ecosystem-card--muted'}`}
            >
              <div>
                <div className="ecosystem-card-header">
                  <img className="ecosystem-logo" src={ecosystem.logo} alt={`${ecosystem.name} logo`} />
                  <h2>{ecosystem.name}</h2>
                </div>
                <p>{ecosystem.description}</p>
                <div className="ecosystem-meta">
                  <div className="ecosystem-meta__info">
                    <Tag
                      severity={available ? 'success' : 'secondary'}
                      value={available ? 'Available now' : 'Coming soon'}
                    />
                    <span>{ecosystem.proposalShortPlural}</span>
                  </div>
                  {available ? (
                    <Button
                      label="Open"
                      icon="pi pi-arrow-right"
                      iconPos="right"
                      text
                      size="small"
                      className="ecosystem-meta__open"
                      onClick={() => navigate(`/ecosystem/${ecosystem.id}`)}
                    />
                  ) : null}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

function EcosystemDashboard() {
  const { ecosystemId } = useParams();
  const ecosystem = ecosystemsById[ecosystemId];
  const emptyDataset = useMemo(() => ({
    nodes: [],
    links: {},
    authorship: {},
    classification: {},
    conformity: {},
    meta: {},
  }), []);
  const availableSnapshots = useMemo(() => getAvailableSnapshots(ecosystemId), [ecosystemId]);
  const [selectedSnapshot, setSelectedSnapshot] = useState(availableSnapshots[0] ?? null);
  const [highlightedAuthor, setHighlightedAuthor] = useState('');
  const [collaborationLayoutMode, setCollaborationLayoutMode] = useState('balanced');
  const [highlightedDependencyProposal, setHighlightedDependencyProposal] = useState('');
  const [dependencyFilterText, setDependencyFilterText] = useState('');
  const [dependencyIncludeConnections, setDependencyIncludeConnections] = useState(true);
  const [selectedDependencyMetricsApproach, setSelectedDependencyMetricsApproach] = useState('explicit_dependencies');
  const [wordCloudFilterText, setWordCloudFilterText] = useState('');
  const [highlightedConformityProposal, setHighlightedConformityProposal] = useState('');

  useEffect(() => {
    setSelectedSnapshot((current) => {
      if (current && availableSnapshots.includes(current)) {
        return current;
      }
      return availableSnapshots[0] ?? null;
    });
  }, [ecosystemId, availableSnapshots]);

  const selectedDataset = ecosystem?.status === 'available'
    ? getDatasetForSelection(ecosystemId, selectedSnapshot)
    : emptyDataset;
  const {
    yearData,
    wordCloudData,
    conformityRows,
    conformityFailedChecks,
    classificationDistributions,
    classificationTimeline,
    classificationCategoryDomains,
    classificationChordData,
    topAuthors,
    authorContributionHistogram,
    collaborationNetwork,
    collaborationMetricsRows,
    dependencyMetrics,
  } = buildDashboardData(selectedDataset);
  const dependencyMetricsApproachOptions = useMemo(
    () => LINK_TYPE_OPTIONS.filter(
      (option) => dependencyMetrics?.by_approach?.[option.value]
    ),
    [dependencyMetrics]
  );
  const activeDependencyMetricsApproach = dependencyMetricsApproachOptions.some(
    (option) => option.value === selectedDependencyMetricsApproach
  )
    ? selectedDependencyMetricsApproach
    : (dependencyMetricsApproachOptions[0]?.value || 'explicit_dependencies');
  const activeDependencyMetrics = dependencyMetrics?.by_approach?.[activeDependencyMetricsApproach] || {
    summary: {},
    per_bip: [],
  };
  const availableProposalIds = useMemo(
    () => (selectedDataset?.nodes || [])
      .map((node) => normalizeProposalFilterValue(node?.id))
      .filter(Boolean)
      .sort((left, right) => Number(left) - Number(right)),
    [selectedDataset]
  );
  const selectedWordCloudProposalIds = useMemo(
    () => parseProposalFilterExpression(wordCloudFilterText, availableProposalIds),
    [availableProposalIds, wordCloudFilterText]
  );
  const selectedDependencyProposalIds = useMemo(
    () => parseProposalFilterExpression(dependencyFilterText, availableProposalIds),
    [availableProposalIds, dependencyFilterText]
  );
  const filteredWordCloudData = useMemo(
    () => buildWordCloudData(selectedDataset?.nodes || [], selectedWordCloudProposalIds),
    [selectedDataset, selectedWordCloudProposalIds]
  );
  const hasWordCloudFilter = wordCloudFilterText.trim().length > 0;
  const hasDependencyFilter = dependencyFilterText.trim().length > 0;

  useEffect(() => {
    setWordCloudFilterText((current) => {
      if (!current.trim()) {
        return current;
      }

      const normalized = parseProposalFilterExpression(current, availableProposalIds);
      return normalized.length ? current : '';
    });
  }, [availableProposalIds]);

  useEffect(() => {
    setDependencyFilterText((current) => {
      if (!current.trim()) {
        return current;
      }

      const normalized = parseProposalFilterExpression(current, availableProposalIds);
      return normalized.length ? current : '';
    });
  }, [availableProposalIds]);

  useEffect(() => {
    setHighlightedConformityProposal((current) => {
      if (!current.trim()) {
        return current;
      }

      const normalized = normalizeProposalFilterValue(current);
      return availableProposalIds.includes(normalized) ? current : '';
    });
  }, [availableProposalIds]);

  useEffect(() => {
    if (!dependencyMetricsApproachOptions.some((option) => option.value === selectedDependencyMetricsApproach)) {
      setSelectedDependencyMetricsApproach(dependencyMetricsApproachOptions[0]?.value || 'explicit_dependencies');
    }
  }, [dependencyMetricsApproachOptions, selectedDependencyMetricsApproach]);

  if (!ecosystem) {
    return (
      <section className="content">
        <h1>Unknown Ecosystem</h1>
        <p>The selected ecosystem does not exist in this frontend configuration.</p>
        <p><Link to="/">Back to ecosystem selection</Link></p>
      </section>
    );
  }

  if (ecosystem.status !== 'available') {
    return (
      <section className="content">
        <h1>{ecosystem.name}</h1>
        <p>This ecosystem is listed intentionally, but its adapter has not been implemented yet.</p>
        <p><Link to="/">Back to ecosystem selection</Link></p>
      </section>
    );
  }
  const collaborationAuthorOptions = collaborationNetwork.nodes
    .map((node) => String(node.id || ''))
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right));
  const dependencyProposalOptions = availableProposalIds;
  const snapshotOptions = availableSnapshots.map((snapshot) => ({
    label: snapshot === 'current' ? 'Current' : snapshot,
    value: snapshot,
  }));
  const sourceRepositories = ecosystem.sourceRepositories || [];

  return (
    <section className="content">
      <div className="dashboard-toolbar">
        <div className="dashboard-toolbar__copy">
          <div className="dashboard-title-row">
            <img className="dashboard-title-logo" src={ecosystem.logo} alt={`${ecosystem.name} logo`} />
            <h1>{ecosystem.proposalPlural}</h1>
          </div>
          <p>
            {ecosystem.proposalPlural} are the main specification documents of the Bitcoin ecosystem, defining features,
            behavior, and also processual or informational aspects. While several catalogs exist, the most prominent one
            is maintained on GitHub and serves as the primary data source for the analyses below.
          </p>
          <ul>
            {sourceRepositories.map((repository) => {
              const href = getSourceRepositoryHref(repository);

              return (
                <li key={repository}>
                  {href ? (
                    <a href={href} target="_blank" rel="noreferrer">
                      {repository}
                    </a>
                  ) : repository}
                </li>
              );
            })}
          </ul>
        </div>
      </div>
      <div className="dashboard-sticky-controls">
        <label htmlFor="snapshot-select" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
          SNAPSHOT
        </label>
        <Dropdown
          inputId="snapshot-select"
          value={selectedSnapshot}
          options={snapshotOptions}
          onChange={(event) => setSelectedSnapshot(event.value)}
          placeholder="Select snapshot date"
          className="w-full"
        />
      </div>
      <section className="dashboard-section">
            <div className="dashboard-section__header">
              <h2 className="dashboard-section__title">Authorship Patterns</h2>
            </div>
            <ExportableCard className="mb-4" exportTitle="Creation Over Time">
              <h3>Creation Over Time</h3>
              <p>
                Creation date of {ecosystem.proposalShortPlural} according to date provided in preamble.
              </p>
              <div data-export-target="true">
                <ProposalTimelineChart data={yearData} width={1200} height={420} />
              </div>
            </ExportableCard>
            <div className="dashboard-grid dashboard-grid--two-up">
              <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Top 10 Authors">
                <h3>Top 10 Authors</h3>
                <p>
                  Preamble authorship counts for the most mentioned contributors.
                </p>
                <div data-export-target="true">
                  <TopAuthorsChart data={{ topAuthors }} width={640} height={410} />
                </div>
              </ExportableCard>
              <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Authorship Distribution">
                <h3>Authorship Distribution</h3>
                <p>
                  Number of preamble authors who have written a given number of {ecosystem.proposalShortPlural}.
                </p>
                <div data-export-target="true">
                  <AuthorContributionHistogram data={authorContributionHistogram} width={640} height={410} />
                </div>
              </ExportableCard>
            </div>
            
            <ExportableCard className="mb-4" exportTitle="Collaboration Network">
              <h3>Collaboration Network</h3>
              <p>
                {ecosystem.acronym} co-authorship according to preamble visualized as collaboration graph.
              </p>
              <div className="network-finder">
                <div className="network-finder__copy">
                  <strong>Author Search</strong>
                </div>
                <div className="network-finder__controls">
                  <InputText
                    value={highlightedAuthor}
                    onChange={(event) => setHighlightedAuthor(event.target.value)}
                    placeholder="Type an author name"
                    list="author-collaboration-options"
                  />
                  <datalist id="author-collaboration-options">
                    {collaborationAuthorOptions.map((author) => (
                      <option key={author} value={author} />
                    ))}
                  </datalist>
                  <Button
                    type="button"
                    label="Clear"
                    severity="secondary"
                    text
                    onClick={() => setHighlightedAuthor('')}
                    disabled={!highlightedAuthor.trim()}
                  />
                </div>
              </div>
              <div className="network-layout-picker">
                <div className="network-layout-picker__label">Layout</div>
                <div className="network-layout-picker__options">
                  {COLLABORATION_LAYOUT_OPTIONS.map((option) => (
                    <label key={option.value} className="network-layout-picker__option">
                      <RadioButton
                        inputId={`collaboration-layout-${option.value}`}
                        name="collaboration-layout"
                        value={option.value}
                        onChange={(event) => setCollaborationLayoutMode(event.value)}
                        checked={collaborationLayoutMode === option.value}
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div data-export-target="true">
                <AuthorCollaborationNetwork
                  data={collaborationNetwork}
                  width={1200}
                  height={700}
                  highlightAuthor={highlightedAuthor}
                  layoutMode={collaborationLayoutMode}
                />
              </div>
            </ExportableCard>
            <Card className="mb-4">
              <h3>Collaboration Metrics</h3>
               <p>{ecosystem.acronym} co-authorship according to preamble ...TODO.</p>
              <AuthorCentralityTable
                rows={collaborationMetricsRows}
                defaultSortField="eigenvector"
                columns={[
                  { field: 'clusterId', header: 'Cluster', format: 'integer' },
                  { field: 'clusterSize', header: 'Cluster Size', format: 'integer' },
                  { field: 'rawDegree', header: 'Degree', format: 'integer' },
                  { field: 'weightedDegree', header: 'Weighted Degree', format: 'integer' },
                  { field: 'normalizedDegree', header: 'Normalized Degree', digits: 4 },
                  { field: 'eigenvector', header: 'Eigenvector Centrality', digits: 4 },
                  { field: 'weightedEigenvector', header: 'Weighted Eigenvector', digits: 4 },
                ]}
              />
            </Card>
            <ExportableCard className="mb-4" exportTitle="Word Cloud of Document Text">
              <h3>Word Cloud of Document Text</h3>
              <p>
                Highlighting the most frequent terms across the selected proposal corpus.
              </p>
              <div className="wordcloud-filter">
                <div className="wordcloud-filter__copy">
                  <strong>Filter proposals:</strong>
                </div>
                <div className="wordcloud-filter__controls">
                  <InputText
                    value={wordCloudFilterText}
                    onChange={(event) => setWordCloudFilterText(event.target.value)}
                    placeholder="e.g. 2,4,30-35,99"
                  />
                  <Button
                    type="button"
                    label="Clear"
                    severity="secondary"
                    text
                    onClick={() => setWordCloudFilterText('')}
                    disabled={!hasWordCloudFilter}
                  />
                </div>
              </div>
              <div data-export-target="true">
                <WordCloud words={hasWordCloudFilter ? filteredWordCloudData : wordCloudData} width={1250} height={600} />
              </div>
            </ExportableCard>
          </section>
          <section className="dashboard-section">
          <div className="dashboard-section__header">
            <h2 className="dashboard-section__title">Classification</h2>
          </div>
          {CLASSIFICATION_DIMENSIONS.map((dimension) => (
            <ExportableCard key={dimension.field} className="mb-4" exportTitle={`${ecosystem.proposalShortPlural} by ${dimension.label}`}>
              <h3>{ecosystem.proposalShortPlural} by {dimension.label}</h3>
              <div className="dashboard-grid dashboard-grid--classification classification-card__grid" data-export-target="true">
                <div className="classification-card__panel">
                  <ClassificationPieChart
                    dimension={dimension.field}
                    colorDomain={classificationCategoryDomains[dimension.field]}
                    data={classificationDistributions[dimension.field]}
                    width={400}
                    height={250}
                  />
                </div>
                <div className="classification-card__panel">
                  <ClassificationStackedTimelineChart
                    categoryDomains={classificationCategoryDomains}
                    dimensions={CLASSIFICATION_DIMENSIONS}
                    selectedDimensions={[dimension.field]}
                    timelineData={classificationTimeline}
                    width={700}
                    height={250}
                  />
                </div>
              </div>
            </ExportableCard>
          ))}
          <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Pairwise Classification Chord Diagram">
            <h3>Pairwise Classification Chord Diagram</h3>
            <p>This chord diagram connects layer, status, and type categories across all pairwise combinations.</p>
            <div data-export-target="true">
              <ClassificationChordDiagram data={classificationChordData} width={1000} height={800} />
            </div>
          </ExportableCard>
          </section>
          <section className="dashboard-section">
          <div className="dashboard-section__header">
            <h2 className="dashboard-section__title">Dependencies</h2>
          </div>
          <ExportableCard className="mb-4" exportTitle={`${ecosystem.acronym} Relationship Network`}>
            <h3>{ecosystem.acronym} Relationship Network</h3>
            <p>
              This graph visualizes three relationship-extraction approaches in the selected ecosystem:
              explicit dependencies (preamble), explicit references (regex), and implicit dependencies (LLM).
            </p>
            <div className="network-finder">
              <div className="network-finder__copy">
                <strong>Find proposal.</strong>
                <span>Search a proposal ID to highlight and center its node in the network.</span>
              </div>
              <div className="network-finder__controls">
                <InputText
                  value={highlightedDependencyProposal}
                  onChange={(event) => setHighlightedDependencyProposal(event.target.value)}
                  placeholder="Type a proposal ID"
                  list="dependency-proposal-options"
                />
                <datalist id="dependency-proposal-options">
                  {dependencyProposalOptions.map((proposalId) => (
                    <option key={proposalId} value={proposalId} />
                  ))}
                </datalist>
                <Button
                  type="button"
                  label="Clear"
                  severity="secondary"
                  text
                  onClick={() => setHighlightedDependencyProposal('')}
                  disabled={!highlightedDependencyProposal.trim()}
                />
              </div>
            </div>
            <div className="wordcloud-filter">
              <div className="wordcloud-filter__copy">
                <strong>Filter proposals.</strong>
                <span>Use comma-separated IDs or ranges like `2,4,30-35,99`.</span>
              </div>
              <div className="wordcloud-filter__controls">
                <InputText
                  value={dependencyFilterText}
                  onChange={(event) => setDependencyFilterText(event.target.value)}
                  placeholder="e.g. 2,4,30-35,99"
                />
                <label className="dependency-filter-checkbox">
                  <input
                    type="checkbox"
                    checked={dependencyIncludeConnections}
                    onChange={(event) => setDependencyIncludeConnections(event.target.checked)}
                  />
                  <span>incl. connections</span>
                </label>
                <Button
                  type="button"
                  label="Clear"
                  severity="secondary"
                  text
                  onClick={() => setDependencyFilterText('')}
                  disabled={!hasDependencyFilter}
                />
              </div>
            </div>
            <NetworkDiagram
              data={selectedDataset}
              width={1200}
              height={700}
              highlightProposal={highlightedDependencyProposal}
              proposalFilterIds={selectedDependencyProposalIds}
              includeConnections={dependencyIncludeConnections}
            />
          </ExportableCard>
          <Card className="mb-4">
            <h3>Relationship Graph Metrics</h3>
            <p>
              Compare simple graph-level structure and per-{ecosystem.proposalShort} centrality measures across
              explicit dependencies, explicit references, and implicit dependencies.
            </p>
            <div className="dependency-metrics-toolbar">
              <div className="dependency-metrics-toolbar__copy">
                <strong>Reference approach.</strong>
                <span>Select which extracted relationship set should drive the metrics below.</span>
              </div>
              <Dropdown
                value={activeDependencyMetricsApproach}
                options={dependencyMetricsApproachOptions}
                onChange={(event) => setSelectedDependencyMetricsApproach(event.value)}
                placeholder="Select approach"
                className="dependency-metrics-toolbar__dropdown"
              />
            </div>
            <div className="analysis-grid dependency-metrics-summary">
              <div className="analysis-stat">
                <h4>Nodes</h4>
                <p>{activeDependencyMetrics.summary?.node_count ?? 0}</p>
              </div>
              <div className="analysis-stat">
                <h4>Edges</h4>
                <p>{activeDependencyMetrics.summary?.edge_count ?? 0}</p>
              </div>
              <div className="analysis-stat">
                <h4>Isolated Nodes</h4>
                <p>{activeDependencyMetrics.summary?.isolated_node_count ?? 0}</p>
              </div>
              <div className="analysis-stat">
                <h4>Circular Dependencies</h4>
                <p>{activeDependencyMetrics.summary?.circular_dependency_count ?? 0}</p>
              </div>
              <div className="analysis-stat">
                <h4>Density</h4>
                <p>{Number(activeDependencyMetrics.summary?.density || 0).toFixed(4).replace(/\.?0+$/, '')}</p>
              </div>
            </div>
            <ProposalGraphMetricsTable
              rows={activeDependencyMetrics.per_bip || []}
              proposalShortLabel={ecosystem.acronym || 'IP'}
              defaultSortField="pagerank"
              defaultSortOrder={-1}
            />
          </Card>
          <ExportableCard className="mb-4" exportTitle="Comparison of Pairwise Relationship Extraction Approach">
            <h3>Comparison of Pairwise Relationship Extraction Approach</h3>
            <p>
              These heatmaps compare each extraction approach against each possible baseline. The first matrix combines
              hits and missed baseline coverage in one cell; the second shows edges found only by the selected approach.
            </p>
            <DependencyComparisonHeatmaps
              pairwiseComparisons={dependencyMetrics?.pairwise_comparisons || {}}
              proposalShortLabel={ecosystem.acronym || 'BIP'}
            />
          </ExportableCard>
      </section>
      <section className="dashboard-section">
        <div className="dashboard-section__header">
          <h2 className="dashboard-section__title">
            Formal Conformity
            <Tag
              className="dashboard-section__tag"
              severity="warning"
              value="Experimental"
            />
          </h2>
        </div>
        <Card className="mb-4">
          <h3>Definition</h3>
          <p>
            Formal conformity of {ecosystem.proposalShortPlural} according to underlying guidelines, i.e., documented in{' '}
            <a href="https://bips.dev/2/" target="_blank" rel="noreferrer">BIP2</a>
            {' '}and{' '}
            <a href="https://bips.dev/3/" target="_blank" rel="noreferrer">BIP3</a>
            , whereas the latter replaced the former as of January 2026. Conformity score (0-100) is computed based on
            automated checks. For details on failed checks, hover over the bubbles.
          </p>
          <div className="network-finder">
            <div className="network-finder__copy">
              <strong>Find proposal:</strong>
            </div>
            <div className="network-finder__controls">
              <InputText
                value={highlightedConformityProposal}
                onChange={(event) => setHighlightedConformityProposal(event.target.value)}
                placeholder="Type a proposal ID"
                list="conformity-proposal-options"
              />
              <datalist id="conformity-proposal-options">
                {dependencyProposalOptions.map((proposalId) => (
                  <option key={proposalId} value={proposalId} />
                ))}
              </datalist>
              <Button
                type="button"
                label="Clear"
                severity="secondary"
                text
                onClick={() => setHighlightedConformityProposal('')}
                disabled={!highlightedConformityProposal.trim()}
              />
            </div>
          </div>
        </Card>
        <div className="dashboard-grid dashboard-grid--two-up">
          <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="BIP2 Conformity">
            <h3>BIP2 Conformity</h3>
            <p>
              Distribution of proposal-level conformity scores under BIP2.
            </p>
            <div data-export-target="true">
              <FormalConformitySwarmPlot
                rows={conformityRows}
                proposalShortLabel={ecosystem.acronym || 'IP'}
                highlightProposal={highlightedConformityProposal}
                standardKey="bip2"
                width={620}
                height={420}
              />
            </div>
          </ExportableCard>
          <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="BIP3 Conformity">
            <h3>BIP3 Conformity</h3>
            <p>
              Distribution of proposal-level conformity scores under BIP3.
            </p>
            <div data-export-target="true">
              <FormalConformitySwarmPlot
                rows={conformityRows}
                proposalShortLabel={ecosystem.acronym || 'IP'}
                highlightProposal={highlightedConformityProposal}
                standardKey="bip3"
                width={620}
                height={420}
              />
            </div>
          </ExportableCard>
        </div>
        <div className="dashboard-grid dashboard-grid--two-up">
          <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Most Failed BIP2 Checks">
            <h3>Most Failed BIP2 Checks</h3>
            <p>
              Frequency of failed formal checks under BIP2 across the selected snapshot.
            </p>
            <div data-export-target="true">
              <ConformityFailedChecksHistogram
                data={conformityFailedChecks.bip2}
                proposalShortLabel={ecosystem.acronym || 'BIP'}
                width={620}
                height={390}
                barColor="#e45756"
                barHoverColor="#b63f3e"
                ariaLabel="Most failed BIP2 conformity checks"
              />
            </div>
          </ExportableCard>
          <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Most Failed BIP3 Checks">
            <h3>Most Failed BIP3 Checks</h3>
            <p>
              Frequency of failed formal checks under BIP3 across the selected snapshot.
            </p>
            <div data-export-target="true">
              <ConformityFailedChecksHistogram
                data={conformityFailedChecks.bip3}
                proposalShortLabel={ecosystem.acronym || 'BIP'}
                width={620}
                height={390}
                barColor="#f08c00"
                barHoverColor="#e67700"
                ariaLabel="Most failed BIP3 conformity checks"
              />
            </div>
          </ExportableCard>
        </div>
      </section>
    </section>
  );
}

function AboutPage() {
  return (
    <section className="content" style={{ padding: '2rem' }}>
      <h1>About This Project</h1>
      <p>
        This app is evolving from a Bitcoin-focused explorer into a more general proposal-analysis frontend.
        Bitcoin is the first implemented ecosystem, but the repo is now being organized so other ecosystems
        such as Nostr NIPs or Tor proposals can be added behind the same navigation model.
      </p>
    </section>
  );
}

function AppShell() {
  const { resolvedTheme } = useTheme();

  return (
    <Router>
      <div className={`App App--${resolvedTheme}`}>
        <Navbar />
        <Routes>
          <Route path="/" element={<EcosystemLanding />} />
          <Route path="/ecosystem/:ecosystemId" element={<EcosystemDashboard />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </div>
    </Router>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppShell />
    </ThemeProvider>
  );
}

export default App;
