import { useMemo, useState } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { InputText } from 'primereact/inputtext';
import { getBipUrl, normalizeBipId } from './bipLinks';
import { useDashboardLinkMode, useDashboardSnapshot } from './dashboard/DashboardSnapshotContext';

function truncateTitle(value, maxLength = 40) {
  const text = String(value || '').trim();
  if (!text) {
    return '';
  }
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength).trimEnd()}...`;
}

function formatNumber(value, digits = 4) {
  return Number(value || 0)
    .toFixed(digits)
    .replace(/\.?0+$/, '');
}

export const ProposalGraphMetricsTable = ({
  rows,
  proposalShortLabel = 'IP',
  defaultSortField,
  defaultSortOrder = -1,
}) => {
  const [globalFilter, setGlobalFilter] = useState('');
  const snapshotLabel = useDashboardSnapshot();
  const linkMode = useDashboardLinkMode();

  const filteredRows = useMemo(() => {
    const search = globalFilter.trim().toLowerCase();
    if (!search) {
      return rows;
    }

    return rows.filter((row) =>
      String(row.id || '').toLowerCase().includes(search)
      || String(row.title || '').toLowerCase().includes(search)
    );
  }, [globalFilter, rows]);

  const header = useMemo(() => (
    <div className="centrality-table__header">
      <span className="p-input-icon-left centrality-table__filter">
        <InputText
          value={globalFilter}
          onChange={(event) => setGlobalFilter(event.target.value)}
          placeholder="Filter proposals"
        />
      </span>
    </div>
  ), [globalFilter]);

  return (
    <DataTable
      value={filteredRows}
      header={header}
      sortField={defaultSortField}
      sortOrder={defaultSortOrder}
      removableSort
      scrollable
      scrollHeight="420px"
      size="small"
      className="centrality-table"
      emptyMessage="No proposals found."
    >
      <Column
        field="id"
        header="IP"
        sortable
        body={(row) => {
          const normalized = normalizeBipId(row.id);
          const title = String(row.title || '').trim();
          const shortTitle = truncateTitle(title, 50);
          return (
            <span>
              <a href={getBipUrl(row.id, snapshotLabel, { linkMode })} target="_blank" rel="noreferrer">
                {normalized ? `${proposalShortLabel} ${normalized}` : String(row.id || '')}
              </a>
              {shortTitle ? (
                <span title={title}>{` ${shortTitle}`}</span>
              ) : null}
            </span>
          );
        }}
      />
      <Column field="in_degree" header="In Degree" sortable body={(row) => Number(row.in_degree || 0)} />
      <Column field="out_degree" header="Out Degree" sortable body={(row) => Number(row.out_degree || 0)} />
      <Column
        field="weighted_eigenvector"
        header="Weighted Eigenvector"
        sortable
        body={(row) => formatNumber(row.weighted_eigenvector, 4)}
      />
      
      <Column
        field="pagerank"
        header="PageRank"
        sortable
        body={(row) => formatNumber(row.pagerank, 4)}
      />
      <Column
        field="betweenness"
        header="Betweenness"
        sortable
        body={(row) => formatNumber(row.betweenness, 4)}
      />
    </DataTable>
  );
};
