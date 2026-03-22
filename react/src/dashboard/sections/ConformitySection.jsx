import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { InputText } from 'primereact/inputtext';
import { Tag } from 'primereact/tag';
import { FormalConformitySwarmPlot } from '../../FormalConformitySwarmPlot';
import { ConformityFailedChecksHistogram } from '../../ConformityFailedChecksHistogram';
import { getBipUrl } from '../../bipLinks';
import { ExportableCard } from '../ExportableCard';

export function ConformitySection({
  ecosystem,
  dependencyProposalOptions,
  highlightedConformityProposal,
  setHighlightedConformityProposal,
  conformityRows,
  conformityFailedChecks,
}) {
  return (
    <section className="dashboard-section">
      <div className="dashboard-section__header">
        <h2 className="dashboard-section__title">
          Formal Conformity
          <Tag
            className="dashboard-section__tag"
            severity="warning"
            value="Experimental"
          />
        </h2>
      </div>
      <Card className="mb-4">
        <h3>Definition</h3>
        <p>
          Formal conformity of {ecosystem.proposalShortPlural} according to underlying guidelines, i.e., documented in{' '}
          <a href={getBipUrl(2, null, { linkMode: 'current' })} target="_blank" rel="noreferrer">BIP2</a>
          {' '}and{' '}
          <a href={getBipUrl(3, null, { linkMode: 'current' })} target="_blank" rel="noreferrer">BIP3</a>
          , whereas the latter replaced the former as of January 2026. Conformity score (0-100) is computed based on
          automated checks. For details on failed checks, hover over the bubbles.
        </p>
        <div className="network-finder">
          <div className="network-finder__copy">
            <strong>Find proposal:</strong>
          </div>
          <div className="network-finder__controls">
            <InputText
              value={highlightedConformityProposal}
              onChange={(event) => setHighlightedConformityProposal(event.target.value)}
              placeholder="Type a proposal ID"
              list="conformity-proposal-options"
            />
            <datalist id="conformity-proposal-options">
              {dependencyProposalOptions.map((proposalId) => (
                <option key={proposalId} value={proposalId} />
              ))}
            </datalist>
            <Button
              type="button"
              label="Clear"
              severity="secondary"
              text
              onClick={() => setHighlightedConformityProposal('')}
              disabled={!highlightedConformityProposal.trim()}
            />
          </div>
        </div>
      </Card>
      <div className="dashboard-grid dashboard-grid--two-up">
        <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="BIP2 Conformity">
          <h3>BIP2 Conformity</h3>
          <p>
            Distribution of proposal-level conformity scores under BIP2.
          </p>
          <div>
            <FormalConformitySwarmPlot
              rows={conformityRows}
              proposalShortLabel={ecosystem.acronym || 'IP'}
              highlightProposal={highlightedConformityProposal}
              standardKey="bip2"
              width={620}
              height={420}
            />
          </div>
        </ExportableCard>
        <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="BIP3 Conformity">
          <h3>BIP3 Conformity</h3>
          <p>
            Distribution of proposal-level conformity scores under BIP3.
          </p>
          <div>
            <FormalConformitySwarmPlot
              rows={conformityRows}
              proposalShortLabel={ecosystem.acronym || 'IP'}
              highlightProposal={highlightedConformityProposal}
              standardKey="bip3"
              width={620}
              height={420}
            />
          </div>
        </ExportableCard>
      </div>
      <div className="dashboard-grid dashboard-grid--two-up">
        <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Most Failed BIP2 Checks">
          <h3>Most Failed BIP2 Checks</h3>
          <p>
            Frequency of failed formal checks under BIP2 across the selected snapshot.
          </p>
          <div>
            <ConformityFailedChecksHistogram
              data={conformityFailedChecks.bip2}
              proposalShortLabel={ecosystem.acronym || 'BIP'}
              width={620}
              height={390}
              barColor="#e45756"
              barHoverColor="#b63f3e"
              ariaLabel="Most failed BIP2 conformity checks"
            />
          </div>
        </ExportableCard>
        <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Most Failed BIP3 Checks">
          <h3>Most Failed BIP3 Checks</h3>
          <p>
            Frequency of failed formal checks under BIP3 across the selected snapshot.
          </p>
          <div>
            <ConformityFailedChecksHistogram
              data={conformityFailedChecks.bip3}
              proposalShortLabel={ecosystem.acronym || 'BIP'}
              width={620}
              height={390}
              barColor="#f08c00"
              barHoverColor="#e67700"
              ariaLabel="Most failed BIP3 conformity checks"
            />
          </div>
        </ExportableCard>
      </div>
    </section>
  );
}
