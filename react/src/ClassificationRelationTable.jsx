import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { getBipUrl } from './bipLinks';
import { useDashboardLinkMode, useDashboardSnapshot } from './dashboard/DashboardSnapshotContext';

export const ClassificationRelationTable = ({
  rows,
  includeLayer = false,
  proposalShortLabel = 'IP',
}) => {
  const snapshotLabel = useDashboardSnapshot();
  const linkMode = useDashboardLinkMode();
  const totalCount = rows.reduce((sum, row) => sum + Number(row.count || 0), 0);

  return (
    <DataTable
      value={rows}
      sortField="count"
      sortOrder={-1}
      removableSort
      scrollable
      scrollHeight="460px"
      size="small"
      className="centrality-table"
      emptyMessage="No classification combinations found."
    >
      <Column field="status" header="Status" sortable />
      <Column field="type" header="Type" sortable />
      {includeLayer ? (
        <Column field="layer" header="Layer" sortable />
      ) : null}
      <Column field="count" header={`${proposalShortLabel}s`} sortable body={(row) => Number(row.count || 0)} />
      <Column
        field="share"
        header="Share"
        body={(row) => `${(((Number(row.count || 0) / Math.max(totalCount, 1)) * 100).toFixed(1)).replace(/\.0$/, '')}%`}
      />
      <Column
        field="bips"
        header={proposalShortLabel}
        body={(row) => (
          <span>
            {(row.bips || []).map((bip, index) => (
              <span key={bip}>
                {index > 0 ? ', ' : ''}
                <a
                  href={getBipUrl(bip, snapshotLabel, { linkMode })}
                  target="_blank"
                  rel="noreferrer"
                  style={{ whiteSpace: 'nowrap' }}
                >
                  {`${proposalShortLabel} ${bip}`}
                </a>
              </span>
            ))}
          </span>
        )}
      />
    </DataTable>
  );
};
