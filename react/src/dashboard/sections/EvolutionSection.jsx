import { useEffect, useMemo, useState } from 'react';
import { Dropdown } from 'primereact/dropdown';
import { RadioButton } from 'primereact/radiobutton';
import { EvolutionStatusStackedBarChart } from '../../EvolutionStatusStackedBarChart';
import { ProposalEventTimeline } from '../../ProposalEventTimeline';
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
  const [selectedProposalId, setSelectedProposalId] = useState('');
  const overallEvolution = evolutionPayload?.status_evolution_segmented
    || evolutionPayload?.status_evolution
    || { categories: [], rows: [] };
  const proposalTimelines = useMemo(() => (
    Array.isArray(evolutionPayload?.proposal_timelines) ? evolutionPayload.proposal_timelines : []
  ), [evolutionPayload]);
  const milestoneLabel = evolutionPayload?.meta?.milestones?.[0]?.label || '';
  const milestoneDate = evolutionPayload?.meta?.milestones?.[0]?.date || '';
  const hasData = hasPositiveValues(overallEvolution);
  const proposalTimelineOptions = useMemo(() => proposalTimelines.map((entry) => ({
    label: entry?.title
      ? `${ecosystem.acronym} ${entry.proposal_id} - ${entry.title}`
      : `${ecosystem.acronym} ${entry?.proposal_id || ''}`,
    value: entry?.proposal_id || '',
  })), [ecosystem.acronym, proposalTimelines]);
  const selectedProposalTimeline = useMemo(() => (
    proposalTimelines.find((entry) => entry?.proposal_id === selectedProposalId) || null
  ), [proposalTimelines, selectedProposalId]);

  useEffect(() => {
    setSelectedProposalId((current) => (
      proposalTimelines.some((entry) => entry?.proposal_id === current)
        ? current
        : (proposalTimelines[0]?.proposal_id || '')
    ));
  }, [proposalTimelines]);

  if (!hasData) {
    return null;
  }

  return (
    <section className="dashboard-section">
      <div className="dashboard-section__header">
        <h2 className="dashboard-section__title">Evolution</h2>
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
      {proposalTimelines.length ? (
        <ExportableCard className="mb-4" exportTitle={`${ecosystem.acronym} Event Timeline`}>
          <h3>{ecosystem.acronym} Event Timeline</h3>
          <p>
            Inspect the event history of a specific {ecosystem.acronym}: creation plus all mined status changes. Timeline markers open the historic repository version for the corresponding Git commit.
          </p>
          <div className="dependency-metrics-toolbar">
            <div className="dependency-metrics-toolbar__copy">
              <strong>Select proposal.</strong>
              <span>Choose a {ecosystem.acronym} to inspect its event-level history.</span>
            </div>
            <Dropdown
              value={selectedProposalId}
              options={proposalTimelineOptions}
              onChange={(event) => setSelectedProposalId(event.value)}
              placeholder={`Select ${ecosystem.acronym}`}
              filter
              className="dependency-metrics-toolbar__dropdown"
            />
          </div>
          <ProposalEventTimeline
            timeline={selectedProposalTimeline}
            proposalShortLabel={ecosystem.acronym}
            milestoneDate={milestoneDate}
            milestoneLabel={milestoneLabel}
          />
        </ExportableCard>
      ) : null}
    </section>
  );
}
