import { ClassificationPieChart } from '../../ClassificationPieChart';
import { ClassificationStackedTimelineChart } from '../../ClassificationStackedTimelineChart';
import { ClassificationChordDiagram } from '../../ClassificationChordDiagram';
import { ExportableCard } from '../ExportableCard';
import { CLASSIFICATION_DIMENSIONS } from '../constants';

export function ClassificationSection({
  ecosystem,
  classificationCategoryDomains,
  classificationDistributions,
  classificationTimeline,
  classificationChordData,
}) {
  return (
    <section className="dashboard-section">
      <div className="dashboard-section__header">
        <h2 className="dashboard-section__title">Classification</h2>
      </div>
      {CLASSIFICATION_DIMENSIONS.map((dimension) => (
        <ExportableCard
          key={dimension.field}
          className="mb-4"
          exportTitle={`${ecosystem.proposalShortPlural} by ${dimension.label}`}
        >
          <h3>{ecosystem.proposalShortPlural} by {dimension.label}</h3>
          <div className="dashboard-grid dashboard-grid--classification classification-card__grid">
            <div className="classification-card__panel">
              <ClassificationPieChart
                dimension={dimension.field}
                colorDomain={classificationCategoryDomains[dimension.field]}
                data={classificationDistributions[dimension.field]}
                width={400}
                height={250}
              />
            </div>
            <div className="classification-card__panel">
              <ClassificationStackedTimelineChart
                categoryDomains={classificationCategoryDomains}
                dimensions={CLASSIFICATION_DIMENSIONS}
                selectedDimensions={[dimension.field]}
                timelineData={classificationTimeline}
                width={700}
                height={250}
              />
            </div>
          </div>
        </ExportableCard>
      ))}
      <ExportableCard className="mb-4" style={{ flex: 1 }} exportTitle="Pairwise Classification Chord Diagram">
        <h3>Pairwise Classification Chord Diagram</h3>
        <p>This chord diagram connects layer, status, and type categories across all pairwise combinations.</p>
        <div>
          <ClassificationChordDiagram data={classificationChordData} width={1000} height={800} />
        </div>
      </ExportableCard>
    </section>
  );
}
