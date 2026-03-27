import {
  BODY_EXTRACTED_LLM,
  BODY_EXTRACTED_REGEX,
  DEFAULT_DEPENDENCY_APPROACH,
  LINK_TYPE_OPTIONS,
  PREAMBLE_EXTRACTED,
  normalizeDependencyLinks,
} from './dependencyApproaches';

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
