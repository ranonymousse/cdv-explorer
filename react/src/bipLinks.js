import externalLinks from './externalLinks.json';
import bipLinkIndex from './generated/bipLinkIndex.json';

const BIPS_DEV_BASE_URL = String(externalLinks.bipsDevBaseUrl || '').replace(/\/+$/, '');

const BITCOIN_BIPS_REPOSITORY_URL = String(
  bipLinkIndex.repositoryUrl || externalLinks.bitcoinBipsRepositoryUrl || ''
).replace(/\/+$/, '');

const BITCOIN_BIPS_DEFAULT_BRANCH = String(
  bipLinkIndex.defaultBranch || externalLinks.bitcoinBipsDefaultBranch || 'master'
)
  .replace(/^refs\/remotes\/origin\//, '')
  .replace(/^origin\//, '');

const BIP_FILES = bipLinkIndex.bipFiles || {};
const SNAPSHOT_COMMITS = bipLinkIndex.snapshotCommits || {};
const SNAPSHOT_FILES = bipLinkIndex.snapshotFiles || {};

export function normalizeBipId(value, options = {}) {
  const { lowercaseFallback = false } = options;
  const text = String(value ?? '').trim();
  if (!text) {
    return '';
  }

  const match = text.match(/^(?:bip\s*[- ]*)?0*(\d+)$/i);
  if (match) {
    return String(Number(match[1]));
  }

  return lowercaseFallback ? text.toLowerCase() : text;
}

function buildDefaultFileName(normalizedId) {
  return /^\d+$/.test(normalizedId) ? `bip-${normalizedId.padStart(4, '0')}.mediawiki` : '';
}

function getSnapshotCommit(snapshotLabel) {
  if (!snapshotLabel) {
    return '';
  }

  return SNAPSHOT_COMMITS[snapshotLabel] || '';
}

function getLatestKnownBipFileName(id) {
  const normalizedId = normalizeBipId(id);
  if (!normalizedId) {
    return '';
  }

  return BIP_FILES[normalizedId] || buildDefaultFileName(normalizedId);
}

function getSnapshotBipFileName(id, snapshotLabel) {
  const normalizedId = normalizeBipId(id);
  if (!normalizedId || !snapshotLabel) {
    return '';
  }

  return SNAPSHOT_FILES[snapshotLabel]?.[normalizedId] || '';
}

export function getBipUrl(id, snapshotLabel = null, options = {}) {
  const { linkMode = 'history' } = options;
  const normalizedId = normalizeBipId(id);

  if (linkMode === 'current') {
    return normalizedId && BIPS_DEV_BASE_URL ? `${BIPS_DEV_BASE_URL}/${normalizedId}/` : '#';
  }

  const snapshotFileName = getSnapshotBipFileName(normalizedId, snapshotLabel);
  if (snapshotLabel) {
    if (!BITCOIN_BIPS_REPOSITORY_URL || !snapshotFileName) {
      return '#';
    }

    const commitHash = getSnapshotCommit(snapshotLabel);
    if (!commitHash) {
      return '#';
    }

    return `${BITCOIN_BIPS_REPOSITORY_URL}/blob/${commitHash}/${snapshotFileName}`;
  }

  const fileName = getLatestKnownBipFileName(normalizedId);
  if (!BITCOIN_BIPS_REPOSITORY_URL || !fileName) {
    return '#';
  }

  const ref = BITCOIN_BIPS_DEFAULT_BRANCH;
  return `${BITCOIN_BIPS_REPOSITORY_URL}/blob/${ref}/${fileName}`;
}
