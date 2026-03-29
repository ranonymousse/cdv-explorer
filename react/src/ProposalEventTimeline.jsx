import { Fragment, useEffect, useMemo, useState } from 'react';
import { getBipCommitUrl, getBipUrl } from './bipLinks';
import { getClassificationColorMap } from './classificationColors';
import { useDashboardLinkMode, useDashboardSnapshot } from './dashboard/DashboardSnapshotContext';

const EDGE_PADDING_PERCENT = 8;

function formatDate(value, options) {
  const text = String(value || '').trim();
  if (!text) {
    return '';
  }

  const parsed = new Date(`${text}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return text;
  }

  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'UTC',
    ...options,
  }).format(parsed);
}

function getEventTitle(event) {
  return event.kind === 'creation' ? 'Created' : String(event.label || event.status || 'Status update');
}

function getEventDescription(event) {
  if (event.kind === 'creation') {
    if (event.status) {
      return `Proposal creation. Earliest recorded status: ${event.status}.`;
    }
    return 'Proposal creation.';
  }

  if (event.previous_status && event.previous_status !== event.status) {
    return `Status changed from ${event.previous_status} to ${event.status}.`;
  }

  return `Status recorded as ${event.status}.`;
}

function formatMilestoneLabel(label) {
  if (String(label || '').trim() === 'BIP3 Activation') {
    return 'BIP-3 activation';
  }
  return String(label || '').trim();
}

export function ProposalEventTimeline({
  timeline,
  proposalShortLabel = 'BIP',
  milestoneDate = '',
  milestoneLabel = '',
}) {
  const snapshotLabel = useDashboardSnapshot();
  const linkMode = useDashboardLinkMode();
  const [activeEventKey, setActiveEventKey] = useState('');

  const events = useMemo(() => (Array.isArray(timeline?.events) ? timeline.events : []).map((event, index) => ({
    ...event,
    key: `${event.kind || 'event'}-${event.date || 'unknown'}-${event.status || event.label || 'unknown'}-${index}`,
  })), [timeline]);

  useEffect(() => {
    setActiveEventKey(events[0]?.key || '');
  }, [events]);

  const statusColors = useMemo(() => getClassificationColorMap(
    'status',
    Array.from(new Set(events.map((event) => String(event.status || '').trim()).filter(Boolean)))
  ), [events]);

  const eventDomain = useMemo(() => {
    const timestamps = events
      .map((event) => Date.parse(`${event.date}T00:00:00Z`))
      .filter((value) => !Number.isNaN(value));
    if (!timestamps.length) {
      return null;
    }

    return {
      min: Math.min(...timestamps),
      max: Math.max(...timestamps),
    };
  }, [events]);

  const milestoneOffset = useMemo(() => {
    const timestamp = Date.parse(`${String(milestoneDate || '').trim()}T00:00:00Z`);
    if (!eventDomain || Number.isNaN(timestamp)) {
      return null;
    }
    if (timestamp < eventDomain.min || timestamp > eventDomain.max) {
      return null;
    }
    if (eventDomain.min === eventDomain.max) {
      return 50;
    }

    const normalizedOffset = (timestamp - eventDomain.min) / (eventDomain.max - eventDomain.min);
    return EDGE_PADDING_PERCENT + normalizedOffset * (100 - EDGE_PADDING_PERCENT * 2);
  }, [eventDomain, milestoneDate]);

  const listMilestoneIndex = useMemo(() => {
    const timestamp = Date.parse(`${String(milestoneDate || '').trim()}T00:00:00Z`);
    if (Number.isNaN(timestamp) || events.length < 2) {
      return -1;
    }

    let sawEarlierEvent = false;
    for (let index = 0; index < events.length; index += 1) {
      const eventTimestamp = Date.parse(`${events[index].date}T00:00:00Z`);
      if (Number.isNaN(eventTimestamp)) {
        continue;
      }

      if (eventTimestamp < timestamp) {
        sawEarlierEvent = true;
        continue;
      }

      return sawEarlierEvent ? index : -1;
    }

    return -1;
  }, [events, milestoneDate]);

  if (!timeline || !events.length) {
    return null;
  }

  const proposalLabel = `${proposalShortLabel} ${timeline.proposal_id}`;
  const proposalHref = getBipUrl(timeline.proposal_id, snapshotLabel, { linkMode });

  const getOffsetPercent = (event) => {
    const timestamp = Date.parse(`${event.date}T00:00:00Z`);
    if (!eventDomain || Number.isNaN(timestamp)) {
      return 0;
    }
    if (eventDomain.min === eventDomain.max) {
      return 50;
    }

    const normalizedOffset = (timestamp - eventDomain.min) / (eventDomain.max - eventDomain.min);
    return EDGE_PADDING_PERCENT + normalizedOffset * (100 - EDGE_PADDING_PERCENT * 2);
  };

  return (
    <div className="proposal-event-history">
      <div className="proposal-event-history__summary">
        <div>
          <h4>
            {proposalHref !== '#' ? (
              <a
                className="proposal-event-history__summary-link"
                href={proposalHref}
                target="_blank"
                rel="noreferrer"
              >
                {proposalLabel}
              </a>
            ) : proposalLabel}
            {timeline.title ? (
              <span className="proposal-event-history__summary-title"> ({timeline.title})</span>
            ) : null}
          </h4>
          <p>
            {events.length} recorded events
            {timeline.created ? ` from ${formatDate(timeline.created, { year: 'numeric', month: 'short', day: 'numeric' })}` : ''}
            {timeline.current_status ? (
              <>
                {', current status '}
                <span className="proposal-event-history__badge">{timeline.current_status}</span>
              </>
            ) : null}
            .
          </p>
        </div>
      </div>

      <div className="proposal-event-history__plot-wrap">
        <div className="proposal-event-history__plot" role="img" aria-label={`${proposalLabel} event timeline`}>
          <div className="proposal-event-history__axis" />
          {milestoneOffset != null ? (
            <div
              className="proposal-event-history__milestone"
              style={{ left: `${milestoneOffset}%` }}
              aria-hidden="true"
            >
              <span className="proposal-event-history__milestone-label">
                {formatMilestoneLabel(milestoneLabel || 'Milestone')}
              </span>
            </div>
          ) : null}
          <div className="proposal-event-history__axis-label is-start">
            {formatDate(events[0]?.date, { year: 'numeric', month: 'short', day: 'numeric' })}
          </div>
          <div className="proposal-event-history__axis-label is-end">
            {formatDate(events[events.length - 1]?.date, { year: 'numeric', month: 'short', day: 'numeric' })}
          </div>
          {events.map((event, index) => {
            const color = event.kind === 'creation'
              ? 'var(--chart-focus)'
              : (statusColors[String(event.status || '').trim()] || 'var(--primary-color)');
            const href = getBipCommitUrl(event.commit, {
              id: timeline.proposal_id,
              fallbackSnapshotLabel: snapshotLabel,
            });
            const linkLabel = event.commit ? 'Open commit diff' : 'Open historic version';
            const isActive = activeEventKey === event.key;
            const laneClass = index % 2 === 0 ? 'is-above' : 'is-below';

            return (
              <div
                key={event.key}
                className={`proposal-event-history__marker ${laneClass}${isActive ? ' is-active' : ''}`}
                style={{ left: `${getOffsetPercent(event)}%`, '--event-color': color }}
                onMouseEnter={() => setActiveEventKey(event.key)}
              >
                <div className="proposal-event-history__marker-label">
                  <span>{getEventTitle(event)}</span>
                  <span>{formatDate(event.date, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                </div>
                {href !== '#' ? (
                  <a
                    className="proposal-event-history__dot"
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`${linkLabel} for ${proposalLabel} on ${event.date}`}
                    onFocus={() => setActiveEventKey(event.key)}
                  />
                ) : (
                  <span
                    className="proposal-event-history__dot is-disabled"
                    aria-hidden="true"
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="proposal-event-history__list">
        {events.map((event, index) => {
          const href = getBipCommitUrl(event.commit, {
            id: timeline.proposal_id,
            fallbackSnapshotLabel: snapshotLabel,
          });
          const linkLabel = event.commit ? 'Open commit diff' : 'Open historic version';
          const isActive = activeEventKey === event.key;
          const color = event.kind === 'creation'
            ? 'var(--chart-focus)'
            : (statusColors[String(event.status || '').trim()] || 'var(--primary-color)');

          return (
            <Fragment key={event.key}>
              {index === listMilestoneIndex ? (
                <div className="proposal-event-history__list-milestone" aria-hidden="true">
                  <span>{formatMilestoneLabel(milestoneLabel || 'Milestone')}</span>
                </div>
              ) : null}
              <article
                className={`proposal-event-history__item${isActive ? ' is-active' : ''}`}
                style={{ '--event-color': color }}
                onMouseEnter={() => setActiveEventKey(event.key)}
              >
                <div className="proposal-event-history__item-date">
                  {formatDate(event.date, { year: 'numeric', month: 'short', day: 'numeric' })}
                </div>
                <div className="proposal-event-history__item-body">
                  <div className="proposal-event-history__item-header">
                    <strong>{getEventTitle(event)}</strong>
                  </div>
                  <p>{getEventDescription(event)}</p>
                  <div className="proposal-event-history__item-meta">
                    {event.author ? <span>{event.author}</span> : null}
                    {event.commit ? (
                      href !== '#' ? (
                        <a
                          href={href}
                          target="_blank"
                          rel="noreferrer"
                          aria-label={`${linkLabel} ${event.commit.slice(0, 10)} for ${proposalLabel} on ${event.date}`}
                          title={linkLabel}
                        >
                          <code>{event.commit.slice(0, 10)}</code>
                        </a>
                      ) : (
                        <code>{event.commit.slice(0, 10)}</code>
                      )
                    ) : null}
                    {!event.commit && href !== '#' ? (
                      <a href={href} target="_blank" rel="noreferrer">
                        {linkLabel}
                      </a>
                    ) : null}
                  </div>
                </div>
              </article>
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}
