import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { Tag } from 'primereact/tag';
import { HashRouter as Router, Route, Routes, useNavigate } from 'react-router-dom';
import Navbar from './Navbar';
import './App.scss';
import { EcosystemDashboard } from './dashboard/EcosystemDashboard';
import { ecosystems } from './ecosystems';
import { ThemeProvider, useTheme } from './theme';

function EcosystemLanding() {
  const navigate = useNavigate();

  return (
    <section className="content">
      <h1>Community-Driven Variability Ecosystem Explorer</h1>
      <p>
        Modern decentralized software ecosystems evolve through crowdsourced improvement proposals (IPs) that are continuously shaped and autonomously implemented by independent actors. As a result, these ecosystems exhibit so-called Community-Driven
Variability (CDV), a novel paradigm that extends beyond traditional variability-intensive systems. This page allows to explore IPs of such ecosystems by providing interactive visualizations and insights about their evolution, authorship, classification, conformity, and inter-proposal relationships.
      </p>

      <div className="ecosystem-grid">
        {ecosystems.map((ecosystem) => {
          const available = ecosystem.status === 'available';

          return (
            <Card
              key={ecosystem.id}
              className={`ecosystem-card${available ? '' : ' ecosystem-card--muted'}`}
            >
              <div>
                <div className="ecosystem-card-header">
                  <img className="ecosystem-logo" src={ecosystem.logo} alt={`${ecosystem.name} logo`} />
                  <h2>{ecosystem.name}</h2>
                </div>
                <p>{ecosystem.description}</p>
                <div className="ecosystem-meta">
                  <div className="ecosystem-meta__info">
                    <Tag
                      severity={available ? 'success' : 'secondary'}
                      value={available ? 'Available now' : 'Coming soon'}
                    />
                    <span>{ecosystem.proposalShortPlural}</span>
                  </div>
                  {available ? (
                    <Button
                      label="Open"
                      icon="pi pi-arrow-right"
                      iconPos="right"
                      text
                      size="small"
                      className="ecosystem-meta__open"
                      onClick={() => navigate(`/ecosystem/${ecosystem.id}`)}
                    />
                  ) : null}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

function AboutPage() {
  return (
    <section className="content" style={{ padding: '2rem' }}>
      <h1>About This Project</h1>
      <p>
        This app is evolving from a Bitcoin-focused explorer into a more general proposal-analysis frontend.
        Bitcoin is the first implemented ecosystem, but the repo is now being organized so other ecosystems
        such as Nostr NIPs or Tor proposals can be added behind the same navigation model.
      </p>
    </section>
  );
}

function AppShell() {
  const { resolvedTheme } = useTheme();

  return (
    <Router>
      <div className={`App App--${resolvedTheme}`}>
        <Navbar />
        <Routes>
          <Route path="/" element={<EcosystemLanding />} />
          <Route path="/ecosystem/:ecosystemId" element={<EcosystemDashboard />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </div>
    </Router>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppShell />
    </ThemeProvider>
  );
}

export default App;
