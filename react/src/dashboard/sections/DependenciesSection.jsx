import { useMemo } from 'react';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { NetworkDiagram } from '../../NetworkDiagram';
import { ProposalGraphMetricsTable } from '../../ProposalGraphMetricsTable';
import { DependencyComparisonHeatmaps } from '../../DependencyComparisonHeatmaps';
import { useAnalysisMetricTooltip } from '../../useAnalysisMetricTooltip';
import { ExportableCard } from '../ExportableCard';

export function DependenciesSection({
  ecosystem,
  selectedDataset,
  highlightedDependencyProposal,
  setHighlightedDependencyProposal,
  dependencyProposalOptions,
  dependencyMinRelations,
  setDependencyMinRelations,
  dependencyMinRelationsIncludeConnections,
  setDependencyMinRelationsIncludeConnections,
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
  const {
    showTooltip: showMetricTooltip,
    moveTooltip: moveMetricTooltip,
    hideTooltip: hideMetricTooltip,
  } = useAnalysisMetricTooltip();

  const dependencyMetricCards = useMemo(() => ([
    {
      label: 'Nodes',
      value: activeDependencyMetrics.summary?.node_count ?? 0,
      description: `Total number of distinct ${ecosystem.proposalShortPlural} represented as nodes in the selected relationship graph.`,
    },
    {
      label: 'Edges',
      value: activeDependencyMetrics.summary?.edge_count ?? 0,
      description: `Total number of directed relationships between ${ecosystem.proposalShortPlural} in the selected extraction approach.`,
    },
    {
      label: 'Isolated Nodes',
      value: activeDependencyMetrics.summary?.isolated_node_count ?? 0,
      description: `Number of ${ecosystem.proposalShortPlural} with neither incoming nor outgoing relationships in the selected graph.`,
    },
    {
      label: 'Circular Dependencies',
      value: activeDependencyMetrics.summary?.circular_dependency_count ?? 0,
      description: `Number of dependency cycles detected in the selected relationship graph.`,
    },
    {
      label: 'Density',
      value: Number(activeDependencyMetrics.summary?.density || 0).toFixed(4).replace(/\.?0+$/, ''),
      description: `Share of all possible directed ${ecosystem.acronym}-to-${ecosystem.acronym} links that actually exist. Higher density means a more interconnected graph.`,
    },
  ]), [activeDependencyMetrics.summary, ecosystem.acronym, ecosystem.proposalShortPlural]);

  return (
    <section className="dashboard-section">
      <div className="dashboard-section__header">
        <h2 className="dashboard-section__title">Dependencies</h2>
      </div>
      <ExportableCard className="mb-4" exportTitle={`${ecosystem.acronym} Relationship Network`}>
        <h3>{ecosystem.acronym} Relationship Network</h3>
        <p>
          The graph below shows three {ecosystem.acronym} relationship-extraction approaches. In the <strong>Preamble</strong> approach, we extract explicitly stated dependencies from the preamble only. The <strong>Regex</strong> approach extracts explicit {ecosystem.acronym} references using regular expressions. The <strong>LLM</strong> approach is designed to capture implicit dependencies inferred by the language model.
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
              <span>transient</span>
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
          proposalShortPlural={ecosystem.proposalShortPlural}
          minRelations={dependencyMinRelations}
          setMinRelations={setDependencyMinRelations}
          proposalFilterIds={selectedDependencyProposalIds}
          setProposalFilterText={setDependencyFilterText}
          includeConnections={dependencyIncludeConnections}
          setIncludeConnections={setDependencyIncludeConnections}
          includeThresholdConnections={dependencyMinRelationsIncludeConnections}
          setIncludeThresholdConnections={setDependencyMinRelationsIncludeConnections}
        />
      </ExportableCard>
      <Card className="mb-4">
        <h3>Relationship Graph Metrics</h3>
        <p>
          Compare simple graph-level structure and per-{ecosystem.acronym} centrality measures across
          {' '}Preamble, Regex, and LLM.{' '} 
          <strong>In Degree</strong> measures how many other BIPs refer to a given BIP (incoming relation).{' '}
          <strong>Out Degree</strong> measures how many other BIPs a given BIP refers to (outgoing relation).
          <strong>Weighted Eigenvector</strong> measures how central a BIP is by considering how well-connected the BIPs it is linked to are.{' '}
          <strong>PageRank</strong> is similar, but additionally accounts for direction and distributes importance across outgoing links, giving more weight to BIPs referenced by many others.{' '}
          <strong>Betweenness</strong> measures how often a BIP lies on the shortest paths between other BIPs, indicating its role in connecting otherwise separate parts of the dependency graph. 
        </p>
        <div className="dependency-metrics-toolbar">
          <div className="dependency-metrics-toolbar__copy">
            <strong>Reference approach.</strong>
            <span>Select which extracted relationship set, Preamble, Regex, or LLM, should drive the metrics below.</span>
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
          {dependencyMetricCards.map((metric) => (
            <div
              key={metric.label}
              className="analysis-stat analysis-stat--interactive"
              onMouseEnter={(event) => showMetricTooltip(event, metric.description)}
              onMouseMove={moveMetricTooltip}
              onMouseLeave={hideMetricTooltip}
            >
              <h4>{metric.label}</h4>
              <p>{metric.value}</p>
            </div>
          ))}
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
          This matrix compares Preamble, Regex, and LLM pairwise. Each cell splits into
          three clickable shares: same, missing from the selected approach, and only in the selected approach.
        </p>
        <DependencyComparisonHeatmaps
          pairwiseComparisons={dependencyMetrics?.pairwise_comparisons || {}}
          proposalShortLabel={ecosystem.acronym || 'BIP'}
        />
      </ExportableCard>
    </section>
  );
}
