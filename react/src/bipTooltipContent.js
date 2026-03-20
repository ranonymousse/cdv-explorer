import { getBipUrl } from './bipLinks';

export function renderBipListHtml(bips, snapshotOrOptions = null, options = {}) {
  const snapshotLabel = typeof snapshotOrOptions === 'string' || snapshotOrOptions == null
    ? snapshotOrOptions
    : null;
  const {
    emptyText = 'No BIP list available.',
    label = 'List:',
    linkMode = 'history',
  } = snapshotLabel == null && snapshotOrOptions && typeof snapshotOrOptions === 'object'
    ? snapshotOrOptions
    : options;

  const bipIds = Array.isArray(bips) ? bips : [];
  if (bipIds.length === 0) {
    return emptyText;
  }

  const bipLinks = bipIds
    .map((bip) => `<a href="${getBipUrl(bip, snapshotLabel, { linkMode })}" target="_blank" rel="noreferrer">BIP${bip}</a>`)
    .join(', ');

  return `${label} ${bipLinks}`;
}
