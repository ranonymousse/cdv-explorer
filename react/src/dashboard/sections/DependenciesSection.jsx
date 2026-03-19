import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { NetworkDiagram } from '../../NetworkDiagram';
import { ProposalGraphMetricsTable } from '../../ProposalGraphMetricsTable';
import { DependencyComparisonHeatmaps } from '../../DependencyComparisonHeatmaps';
import { ExportableCard } from '../ExportableCard';

export function DependenciesSection({
  ecosystem,
  selectedDataset,
  highlightedDependencyProposal,
  setHighlightedDependencyProposal,
  dependencyProposalOptions,
  dependencyFilterText,
  setDependencyFilterText,
  dependencyIncludeConnections,
  setDependencyIncludeConnections,
  hasDependencyFilter,
  selectedDependencyProposalIds,
  dependencyMetricsApproachOptions,
  activeDependencyMetricsApproach,
  setSelectedDependencyMetricsApproach,
  activeDependencyMetrics,
  dependencyMetrics,
}) {
  return (
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
  );
}
