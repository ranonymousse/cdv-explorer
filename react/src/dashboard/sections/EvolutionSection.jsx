import { RadioButton } from 'primereact/radiobutton';
import { Tag } from 'primereact/tag';
import { useState } from 'react';
import { EvolutionStatusStackedBarChart } from '../../EvolutionStatusStackedBarChart';
import { ExportableCard } from '../ExportableCard';

function hasPositiveValues(series) {
  return Array.isArray(series?.rows) && series.rows.some((row) => (
    Object.values(row?.values || {}).some((value) => Number(value) > 0)
  ));
}

export function EvolutionSection({
  ecosystem,
  evolutionPayload,
}) {
  const [chartMode, setChartMode] = useState('absolute');
  const overallEvolution = evolutionPayload?.status_evolution_segmented
    || evolutionPayload?.status_evolution
    || { categories: [], rows: [] };
  const milestoneLabel = evolutionPayload?.meta?.milestones?.[0]?.label || '';
  const milestoneDate = evolutionPayload?.meta?.milestones?.[0]?.date || '';
  const hasData = hasPositiveValues(overallEvolution);

  if (!hasData) {
    return null;
  }

  return (
    <section className="dashboard-section">
      <div className="dashboard-section__header">
        <h2 className="dashboard-section__title">
          Evolution
          <Tag
            className="dashboard-section__tag"
            severity="warning"
            value="Experimental"
          />
        </h2>
      </div>
      <ExportableCard className="mb-4" exportTitle={`${ecosystem.acronym} Status Evolution`}>
        <h3>{ecosystem.acronym} Status Evolution</h3>
        <p>
          Stacked status counts reconstructed from proposal Git history using landed commit dates. Bars show quarter-end states, with a separate breakpoint for {milestoneLabel || 'major process changes'}{milestoneDate ? ` on ${milestoneDate}` : ''}.
        </p>
        <div className="network-layout-controls">
          <div className="network-layout-picker">
            <div className="network-layout-picker__label">Mode</div>
            <div className="network-layout-picker__options">
              {[
                { label: 'Absolute', value: 'absolute' },
                { label: 'Relative', value: 'relative' },
              ].map((option) => (
                <label key={option.value} className="network-layout-picker__option">
                  <RadioButton
                    inputId={`evolution-mode-${option.value}`}
                    name="evolution-mode"
                    value={option.value}
                    onChange={(event) => setChartMode(event.value)}
                    checked={chartMode === option.value}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
        <div>
          <EvolutionStatusStackedBarChart
            data={overallEvolution}
            title={`${ecosystem.acronym} Status Evolution`}
            mode={chartMode}
            width={600}
            height={500}
          />
        </div>
      </ExportableCard>
    </section>
  );
}
