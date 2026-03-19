import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { RadioButton } from 'primereact/radiobutton';
import { Card } from 'primereact/card';
import { ProposalTimelineChart } from '../../ProposalTimelineChart';
import { TopAuthorsChart } from '../../TopAuthorsChart';
import { AuthorContributionHistogram } from '../../AuthorContributionHistogram';
import { AuthorCollaborationNetwork } from '../../AuthorCollaborationNetwork';
import { AuthorCentralityTable } from '../../AuthorCentralityTable';
import { WordCloud } from '../../WordCloud';
import { ExportableCard } from '../ExportableCard';
import { COLLABORATION_LAYOUT_OPTIONS } from '../constants';

export function AuthorshipSection({
  ecosystem,
  yearData,
  topAuthors,
  authorContributionHistogram,
  collaborationNetwork,
  collaborationMetricsRows,
  highlightedAuthor,
  setHighlightedAuthor,
  collaborationLayoutMode,
  setCollaborationLayoutMode,
  collaborationAuthorOptions,
  wordCloudFilterText,
  setWordCloudFilterText,
  hasWordCloudFilter,
  filteredWordCloudData,
  wordCloudData,
}) {
  return (
    <section className="dashboard-section">
      <div className="dashboard-section__header">
        <h2 className="dashboard-section__title">Authorship Patterns</h2>
      </div>
      <ExportableCard className="mb-4" exportTitle="Creation Over Time">
        <h3>Creation Over Time</h3>
        <p>
          Creation date of {ecosystem.proposalShortPlural} according to date provided in preamble.
        </p>
        <div data-export-target="true">
          <ProposalTimelineChart data={yearData} width={1200} height={420} />
        </div>
      </ExportableCard>
      <div className="dashboard-grid dashboard-grid--two-up">
        <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Top 10 Authors">
          <h3>Top 10 Authors</h3>
          <p>
            Preamble authorship counts for the most mentioned contributors.
          </p>
          <div data-export-target="true">
            <TopAuthorsChart data={{ topAuthors }} width={640} height={410} />
          </div>
        </ExportableCard>
        <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Authorship Distribution">
          <h3>Authorship Distribution</h3>
          <p>
            Number of preamble authors who have written a given number of {ecosystem.proposalShortPlural}.
          </p>
          <div data-export-target="true">
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
        <div data-export-target="true">
          <AuthorCollaborationNetwork
            data={collaborationNetwork}
            width={1200}
            height={700}
            highlightAuthor={highlightedAuthor}
            layoutMode={collaborationLayoutMode}
          />
        </div>
      </ExportableCard>
      <Card className="mb-4">
        <h3>Collaboration Metrics</h3>
        <p>{ecosystem.acronym} co-authorship according to preamble ...TODO.</p>
        <AuthorCentralityTable
          rows={collaborationMetricsRows}
          defaultSortField="eigenvector"
          columns={[
            { field: 'clusterId', header: 'Cluster', format: 'integer' },
            { field: 'clusterSize', header: 'Cluster Size', format: 'integer' },
            { field: 'rawDegree', header: 'Degree', format: 'integer' },
            { field: 'weightedDegree', header: 'Weighted Degree', format: 'integer' },
            { field: 'normalizedDegree', header: 'Normalized Degree', digits: 4 },
            { field: 'eigenvector', header: 'Eigenvector Centrality', digits: 4 },
            { field: 'weightedEigenvector', header: 'Weighted Eigenvector', digits: 4 },
          ]}
        />
      </Card>
      <ExportableCard className="mb-4" exportTitle="Word Cloud of Document Text">
        <h3>Word Cloud of Document Text</h3>
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
        <div data-export-target="true">
          <WordCloud words={hasWordCloudFilter ? filteredWordCloudData : wordCloudData} width={1250} height={600} />
        </div>
      </ExportableCard>
    </section>
  );
}
