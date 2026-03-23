from collections import Counter, defaultdict
from datetime import date
from typing import Any, Dict, List

from analysis.classification.preprocess import normalize_classification_fields
from ecosystem_config import ACTIVE_ECOSYSTEM


CLASSIFICATION_CONFIG = ACTIVE_ECOSYSTEM.get("classification", {})
CLASSIFICATION_PAPER_CONFIG = CLASSIFICATION_CONFIG.get("paper", {})
BIP3_ALLOWED_STATUSES = {"Draft", "Complete", "Deployed", "Closed"}


def _normalize_status(status: Any) -> str:
    text = str(status or "").strip()
    if not text:
        return ""
    normalized = normalize_classification_fields({"status": text})
    return str(normalized.get("status") or "").strip()


def _parse_event_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None

    candidate = text[:10]
    try:
        return date.fromisoformat(candidate)
    except ValueError:
        return None


def _normalize_proposal_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.isdigit():
        return str(int(text))
    return text


def _infer_standard(status: str) -> str:
    return "bip3" if status in BIP3_ALLOWED_STATUSES else "bip2"


def _fallback_timeline(proposal: Dict[str, Any], id_field: str) -> List[Dict[str, Any]]:
    preamble = proposal.get("raw", {}).get("preamble", {})
    proposal_id = _normalize_proposal_id(preamble.get(id_field))
    status = _normalize_status(preamble.get("status"))
    created_date = _parse_event_date(preamble.get("created"))

    if not proposal_id or not status or created_date is None:
        return []

    return [
        {
            "proposal_id": proposal_id,
            "date": created_date,
            "status": status,
            "standard": _infer_standard(status),
        }
    ]


def _build_status_order(categories: List[str]) -> List[str]:
    configured_order: List[str] = []
    for entry in CLASSIFICATION_PAPER_CONFIG.get("rq2_status_orders", []):
        for status in entry.get("order", []):
            if status not in configured_order:
                configured_order.append(status)

    remaining = sorted(category for category in categories if category not in configured_order)
    return [status for status in configured_order if status in categories] + remaining


def _resolve_bip3_start_date() -> date | None:
    for entry in CLASSIFICATION_PAPER_CONFIG.get("reporting_standards", []):
        if str(entry.get("standard") or "").strip() != "bip3":
            continue
        start_date = _parse_event_date(entry.get("snapshot_from"))
        if start_date is not None:
            return start_date
    return None


def _resolve_effective_standard(
    *,
    active_standard: str | None,
    active_status: str,
    period_end: date,
    bip3_start_date: date | None,
) -> str:
    if active_standard == "bip3":
        return "bip3"

    if (
        active_status in BIP3_ALLOWED_STATUSES
        and bip3_start_date is not None
        and period_end >= bip3_start_date
    ):
        return "bip3"

    return active_standard or _infer_standard(active_status)


def _quarter_start(value: date) -> date:
    quarter_month = ((value.month - 1) // 3) * 3 + 1
    return date(value.year, quarter_month, 1)


def _next_quarter(value: date) -> date:
    if value.month == 10:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 3, 1)


def _quarter_end(value: date) -> date:
    if value.month == 1:
        return date(value.year, 3, 31)
    if value.month == 4:
        return date(value.year, 6, 30)
    if value.month == 7:
        return date(value.year, 9, 30)
    return date(value.year, 12, 31)


def _format_quarter_label(value: date) -> str:
    quarter = ((value.month - 1) // 3) + 1
    return f"{value.year}-Q{quarter}"


def _build_quarter_periods(start_date: date, end_date: date) -> List[date]:
    periods: List[date] = []
    current = _quarter_start(start_date)
    final = _quarter_start(end_date)

    while current <= final:
        periods.append(current)
        current = _next_quarter(current)

    return periods


def _build_evolution_series(
    proposal_timelines: List[List[Dict[str, Any]]],
    periods: List[date],
    ordered_categories: List[str],
    *,
    standard_filter: str | None = None,
) -> Dict[str, Any]:
    bip3_start_date = _resolve_bip3_start_date()
    counts_by_period = {period: Counter() for period in periods}
    bips_by_period = {period: defaultdict(set) for period in periods}

    for timeline in proposal_timelines:
        event_index = 0
        active_status = None
        active_standard = None
        proposal_id = timeline[0]["proposal_id"]

        for period in periods:
            period_end = _quarter_end(period)

            while event_index < len(timeline) and timeline[event_index]["date"] <= period_end:
                active_status = timeline[event_index]["status"]
                active_standard = timeline[event_index]["standard"]
                event_index += 1

            if not active_status:
                continue

            effective_standard = _resolve_effective_standard(
                active_standard=active_standard,
                active_status=active_status,
                period_end=period_end,
                bip3_start_date=bip3_start_date,
            )

            if standard_filter is not None and effective_standard != standard_filter:
                continue

            counts_by_period[period][active_status] += 1
            bips_by_period[period][active_status].add(proposal_id)

    rows = []
    for period in periods:
        values = {status: counts_by_period[period].get(status, 0) for status in ordered_categories}
        bips = {
            status: sorted(
                bips_by_period[period].get(status, set()),
                key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value),
            )
            for status in ordered_categories
        }
        rows.append(
            {
                "period": _format_quarter_label(period),
                "values": values,
                "bips": bips,
            }
        )

    return {
        "categories": ordered_categories,
        "rows": rows,
    }


def prepare_evolution_payload(
    proposal_data: List[Dict[str, Any]],
    snapshot_label: str | None,
    id_field: str,
) -> Dict[str, Any]:
    proposal_timelines: List[List[Dict[str, Any]]] = []
    category_set = set()
    min_date = None
    max_date = None

    for proposal in proposal_data:
        preamble = proposal.get("raw", {}).get("preamble", {})
        proposal_id = _normalize_proposal_id(preamble.get(id_field))
        raw_timeline = proposal.get("history", {}).get("status_timeline", [])

        timeline = []
        for event in raw_timeline if isinstance(raw_timeline, list) else []:
            event_date = _parse_event_date(event.get("date") or event.get("timestamp"))
            status = _normalize_status(event.get("status"))
            if event_date is None or not status or not proposal_id:
                continue
            timeline.append(
                {
                    "proposal_id": proposal_id,
                    "date": event_date,
                    "status": status,
                    "standard": event.get("standard") or _infer_standard(status),
                }
            )

        if not timeline:
            timeline = _fallback_timeline(proposal, id_field=id_field)

        if not timeline:
            continue

        timeline.sort(key=lambda entry: entry["date"])
        proposal_timelines.append(timeline)

        for event in timeline:
            category_set.add(event["status"])
            event_date = event["date"]
            min_date = event_date if min_date is None else min(min_date, event_date)
            max_date = event_date if max_date is None else max(max_date, event_date)

    snapshot_date = _parse_event_date(snapshot_label)
    if snapshot_date is not None:
        max_date = snapshot_date if max_date is None else max(max_date, snapshot_date)

    if min_date is None or max_date is None:
        return {
            "meta": {
                "proposal_count": 0,
                "timeline_count": 0,
                "first_year": None,
                "last_year": None,
                "first_quarter": None,
                "last_quarter": None,
            },
            "status_evolution": {
                "categories": [],
                "rows": [],
            },
        }

    ordered_categories = _build_status_order(list(category_set))
    periods = _build_quarter_periods(min_date, max_date)
    first_period = periods[0]
    last_period = periods[-1]
    categories_by_standard = {
        "bip2": _build_status_order(
            sorted({
                event["status"]
                for timeline in proposal_timelines
                for event in timeline
                if event.get("standard") == "bip2"
            })
        ),
        "bip3": _build_status_order(
            sorted({
                event["status"]
                for timeline in proposal_timelines
                for event in timeline
                if event.get("standard") == "bip3"
            })
        ),
    }

    proposal_ids = {
        _normalize_proposal_id(proposal.get("raw", {}).get("preamble", {}).get(id_field))
        for proposal in proposal_data
        if proposal.get("raw", {}).get("preamble", {}).get(id_field) is not None
    }

    return {
        "meta": {
            "proposal_count": len(proposal_ids),
            "timeline_count": len(proposal_timelines),
            "first_year": first_period.year,
            "last_year": last_period.year,
            "first_quarter": _format_quarter_label(first_period),
            "last_quarter": _format_quarter_label(last_period),
        },
        "status_evolution": _build_evolution_series(
            proposal_timelines,
            periods,
            ordered_categories,
        ),
        "status_evolution_by_standard": {
            "bip2": _build_evolution_series(
                proposal_timelines,
                periods,
                categories_by_standard["bip2"],
                standard_filter="bip2",
            ),
            "bip3": _build_evolution_series(
                proposal_timelines,
                periods,
                categories_by_standard["bip3"],
                standard_filter="bip3",
            ),
        },
    }
