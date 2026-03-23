import { useMemo } from 'react';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { RadioButton } from 'primereact/radiobutton';
import { Card } from 'primereact/card';
import { Tag } from 'primereact/tag';
import { ProposalTimelineChart } from '../../ProposalTimelineChart';
import { TopAuthorsChart } from '../../TopAuthorsChart';
import { AuthorContributionHistogram } from '../../AuthorContributionHistogram';
import { AuthorCollaborationNetwork } from '../../AuthorCollaborationNetwork';
import { AuthorCentralityTable } from '../../AuthorCentralityTable';
import { WordCloud } from '../../WordCloud';
import { useAnalysisMetricTooltip } from '../../useAnalysisMetricTooltip';
import { ExportableCard } from '../ExportableCard';
import { COLLABORATION_LAYOUT_OPTIONS } from '../constants';

export function AuthorshipSection({
  ecosystem,
  yearData,
  topAuthors,
  authorContributionHistogram,
  collaborationNetwork,
  collaborationMetricsSummary,
  collaborationMetricsRows,
  highlightedAuthor,
  setHighlightedAuthor,
  collaborationLayoutMode,
  setCollaborationLayoutMode,
  collaborationMinClusterCollaborations,
  setCollaborationMinClusterCollaborations,
  collaborationAuthorOptions,
  wordCloudFilterText,
  setWordCloudFilterText,
  hasWordCloudFilter,
  filteredWordCloudData,
  wordCloudData,
}) {
  const {
    showTooltip: showMetricTooltip,
    moveTooltip: moveMetricTooltip,
    hideTooltip: hideMetricTooltip,
  } = useAnalysisMetricTooltip();

  const collaborationMetricCards = useMemo(() => ([
    {
      label: 'Nodes',
      value: collaborationMetricsSummary?.nodeCount ?? 0,
      description: 'Total number of distinct authors, including solo-only authors with no co-authorship links.',
    },
    {
      label: 'Edges',
      value: collaborationMetricsSummary?.edgeCount ?? 0,
      description: 'Number of distinct author pairs that have co-authored at least one proposal together.',
    },
    {
      label: 'Isolated Nodes',
      value: collaborationMetricsSummary?.isolatedAuthorCount ?? 0,
      description: 'Authors with degree 0, meaning they appear in the corpus but never co-author a proposal with anyone else. For readability, they are shown together in one shared display cluster.',
    },
    {
      label: 'Clusters',
      value: collaborationMetricsSummary?.clusterCount ?? 0,
      description: 'Number of display clusters in the collaboration graph and table. Authors with no co-authorship links are grouped into one shared cluster for readability.',
    },
    {
      label: 'Density',
      value: Number(collaborationMetricsSummary?.density || 0).toFixed(4).replace(/\.?0+$/, ''),
      description: 'Share of all possible author-to-author links that actually exist. Higher density means collaboration is more broadly interconnected.',
    },
  ]), [collaborationMetricsSummary]);

  return (
    <section className="dashboard-section">
      <div className="dashboard-section__header">
        <h2 className="dashboard-section__title">Authorship Diversity</h2>
      </div>
      <ExportableCard className="mb-4" exportTitle="Creation Over Time">
        <h3>Creation Over Time</h3>
        <p>
          Creation date of {ecosystem.proposalShortPlural} according to date provided in preamble.
        </p>
        <div>
          <ProposalTimelineChart data={yearData} width={1200} height={420} />
        </div>
      </ExportableCard>
      <div className="dashboard-grid dashboard-grid--two-up">
        <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Top 10 Authors">
          <h3>Top 10 Authors</h3>
          <p>
            Preamble authorship counts for the most mentioned contributors.
          </p>
          <div>
            <TopAuthorsChart data={{ topAuthors }} width={640} height={410} />
          </div>
        </ExportableCard>
        <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Authorship Distribution">
          <h3>Authorship Distribution</h3>
          <p>
            Number of preamble authors who have written a given number of {ecosystem.proposalShortPlural}.
          </p>
          <div>
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
        <div className="network-layout-controls">
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
          <div className="network-layout-picker network-layout-picker--filter">
            <div className="network-layout-picker__label">Filter</div>
            <label className="network-layout-threshold">
              <span className="network-layout-threshold__copy">Only show clusters with</span>
              <InputText
                value={collaborationMinClusterCollaborations}
                onChange={(event) => setCollaborationMinClusterCollaborations(event.target.value.replace(/[^\d]/g, ''))}
                placeholder="0"
                inputMode="numeric"
                className="network-layout-threshold__input"
              />
              <span className="network-layout-threshold__suffix">or more collaborations.</span>
            </label>
          </div>
        </div>
        <div>
          <AuthorCollaborationNetwork
            data={collaborationNetwork}
            width={1200}
            height={700}
            highlightAuthor={highlightedAuthor}
            layoutMode={collaborationLayoutMode}
            minClusterCollaborations={collaborationMinClusterCollaborations}
          />
        </div>
      </ExportableCard>
      <Card className="mb-4">
        <h3>Collaboration Metrics</h3>
        <p>
          {ecosystem.acronym} co-authorship according to preamble. 
          Author names marked with <strong><code>*</code></strong> are in the top 10 by authored {ecosystem.proposalShortPlural}. <strong>Cluster</strong>
          {' '}and <strong>Cluster Size</strong> show the connected co-authorship group an author belongs to and how large
          that group is. Authors with no co-authorship links are grouped into one shared display cluster for readability.
          <strong>Degree</strong> counts distinct co-authors, <strong>Weighted Degree</strong> counts repeated
          collaborations, and <strong>Weighted Eigenvector</strong> is higher for authors connected to other highly
          collaborative authors.
        </p>
        <div className="analysis-grid collaboration-metrics-summary">
          {collaborationMetricCards.map((metric) => (
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
        <AuthorCentralityTable
          rows={collaborationMetricsRows}
          defaultSortField="weightedEigenvector"
          columns={[
            { field: 'clusterId', header: 'Cluster', format: 'integer' },
            { field: 'clusterSize', header: 'Cluster Size', format: 'integer' },
            { field: 'rawDegree', header: 'Degree', format: 'integer' },
            { field: 'weightedDegree', header: 'Weighted Degree', format: 'integer' },
            { field: 'weightedEigenvector', header: 'Weighted Eigenvector', digits: 4 },
          ]}
        />
      </Card>
      <ExportableCard className="mb-4" exportTitle="Word Cloud of Document Text">
        <h3 className="card-title-with-badge">
          Word Cloud of Document Text
          <Tag
            className="dashboard-section__tag card-title-with-badge__tag"
            severity="warning"
            value="Experimental"
          />
        </h3>
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
        <div>
          <WordCloud words={hasWordCloudFilter ? filteredWordCloudData : wordCloudData} width={1250} height={500} />
        </div>
      </ExportableCard>
    </section>
  );
}
