import { createContext, useContext } from 'react';

const DashboardSnapshotContext = createContext({
  snapshot: null,
  linkMode: 'history',
});

export function DashboardSnapshotProvider({ snapshot, linkMode = 'history', children }) {
  return (
    <DashboardSnapshotContext.Provider value={{
      snapshot: snapshot || null,
      linkMode,
    }}
    >
      {children}
    </DashboardSnapshotContext.Provider>
  );
}

export function useDashboardSnapshot() {
  return useContext(DashboardSnapshotContext).snapshot;
}

export function useDashboardLinkMode() {
  return useContext(DashboardSnapshotContext).linkMode;
}
