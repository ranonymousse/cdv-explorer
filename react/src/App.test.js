import {
  BODY_EXTRACTED_LLM,
  BODY_EXTRACTED_REGEX,
  DEFAULT_DEPENDENCY_APPROACH,
  LINK_TYPE_OPTIONS,
  PREAMBLE_EXTRACTED,
  normalizeDependencyLinks,
} from './dependencyApproaches';
import { getBipUrl } from './bipLinks';

test('dependency link options default to the canonical preamble approach', () => {
  expect(DEFAULT_DEPENDENCY_APPROACH).toBe(PREAMBLE_EXTRACTED);
  expect(LINK_TYPE_OPTIONS.map((option) => option.value)).toEqual([
    PREAMBLE_EXTRACTED,
    BODY_EXTRACTED_REGEX,
    BODY_EXTRACTED_LLM,
  ]);
});

test('normalizes legacy dependency link keys into canonical keys', () => {
  const normalized = normalizeDependencyLinks({
    explicit_references: [{ source: '1', target: '2', value: 1 }],
    explicit_dependencies: {
      requires: [{ source: '2', target: '1', value: 1 }],
      replaces: [],
      superseded_by: [],
    },
    implicit_dependencies: [{ source: '3', target: '2', value: 1 }],
  });

  expect(normalized[BODY_EXTRACTED_REGEX]).toHaveLength(1);
  expect(normalized[PREAMBLE_EXTRACTED].requires).toHaveLength(1);
  expect(normalized[BODY_EXTRACTED_LLM]).toHaveLength(1);
});

test('uses the snapshot commit for historic BIP links when the file exists in that snapshot', () => {
  expect(getBipUrl(2, '2026-03-16', { linkMode: 'history' })).toBe(
    'https://github.com/bitcoin/bips/blob/351ceef2747e46078efaa073246fce54d52e665d/bip-0002.mediawiki'
  );
});

test('falls back to the latest repository file when a historic snapshot file lookup misses', () => {
  expect(getBipUrl(3, '2021-01-01', { linkMode: 'history' })).toBe(
    'https://github.com/bitcoin/bips/blob/master/bip-0003.md'
  );
});
