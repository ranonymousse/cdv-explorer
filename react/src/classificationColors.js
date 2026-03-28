import * as d3 from 'd3';

const PALETTE = [
  ...d3.schemeTableau10,
  ...d3.schemeSet2,
  ...d3.schemeSet3,
];
const FIXED_STATUS_COLORS = {
  Closed: '#868e96',
};

export function getClassificationColorMap(dimension, categories = []) {
  const uniqueCategories = Array.from(
    new Set((categories || []).map((category) => String(category || '').trim()).filter(Boolean))
  );

  return Object.fromEntries(
    uniqueCategories.map((category, index) => {
      if (dimension === 'status' && FIXED_STATUS_COLORS[category]) {
        return [category, FIXED_STATUS_COLORS[category]];
      }
      return [category, PALETTE[index % PALETTE.length]];
    })
  );
}
