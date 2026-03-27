from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List

from analysis.classification.preprocess import normalize_classification_fields
from analysis.proposal_schema import get_changes_in_status
from ecosystem_config import ACTIVE_ECOSYSTEM


CLASSIFICATION_CONFIG = ACTIVE_ECOSYSTEM.get("classification", {})
CLASSIFICATION_PAPER_CONFIG = CLASSIFICATION_CONFIG.get("paper", {})
BIP2_PRIMARY_STATUS_ORDER = [
    "Draft",
    "Active",
    "Proposed",
    "Deferred",
    "Rejected",
    "Withdrawn",
    "Final",
    "Replaced",
    "Obsolete",
]
BIP3_PRIMARY_STATUS_ORDER = ["Draft", "Complete", "Deployed", "Closed"]
BIP2_EXCLUSIVE_STATUSES = set(BIP2_PRIMARY_STATUS_ORDER) - {"Draft"}
BIP3_EXCLUSIVE_STATUSES = {"Complete", "Deployed", "Closed"}


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
    return "bip3" if status in BIP3_EXCLUSIVE_STATUSES else "bip2"


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
            "standard": _resolve_event_standard(None, created_date, status),
        }
    ]


def _build_status_order(categories: List[str]) -> List[str]:
    configured_order: List[str] = []
    for entry in CLASSIFICATION_PAPER_CONFIG.get("rq1_status_orders", []):
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


def _resolve_standard_from_date(event_date: date | None) -> str | None:
    if event_date is None:
        return None

    matched_standard = None
    for entry in CLASSIFICATION_PAPER_CONFIG.get("reporting_standards", []):
        standard = str(entry.get("standard") or "").strip()
        if not standard:
            continue

        start_date = _parse_event_date(entry.get("snapshot_from"))
        end_date = _parse_event_date(entry.get("snapshot_to"))

        if start_date is not None and event_date < start_date:
            continue
        if end_date is not None and event_date > end_date:
            continue

        matched_standard = standard
        break

    return matched_standard


def _resolve_event_standard(raw_standard: Any, event_date: date | None, status: str) -> str:
    standard = str(raw_standard or "").strip()
    if standard:
        return standard

    if status in BIP3_EXCLUSIVE_STATUSES:
        return "bip3"
    if status in BIP2_EXCLUSIVE_STATUSES:
        return "bip2"

    return _resolve_standard_from_date(event_date) or _infer_standard(status)


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


def _quarter_number(value: date) -> int:
    return ((value.month - 1) // 3) + 1


def _format_quarter_label(value: date) -> str:
    return f"{value.year}-Q{_quarter_number(value)}"


def _build_periods(start_date: date, end_date: date, *, breakpoint_date: date | None = None) -> List[Dict[str, Any]]:
    periods: List[Dict[str, Any]] = []
    current = _quarter_start(start_date)
    final = _quarter_start(end_date)

    while current <= final:
        quarter_end = _quarter_end(current)
        quarter_label = _format_quarter_label(current)

        if breakpoint_date is not None and current <= breakpoint_date <= quarter_end:
            pre_breakpoint_end = breakpoint_date - timedelta(days=1)
            if current <= pre_breakpoint_end:
                periods.append(
                    {
                        "key": f"{quarter_label}-pre-bip3",
                        "label": quarter_label,
                        "start": current,
                        "end": pre_breakpoint_end,
                        "kind": "milestone",
                        "milestone_label": "BIP3 Activation",
                    }
                )

            remainder_start = breakpoint_date
            if remainder_start <= quarter_end:
                periods.append(
                    {
                        "key": f"{quarter_label}-post-bip3",
                        "label": quarter_label,
                        "start": remainder_start,
                        "end": quarter_end,
                        "kind": "milestone_remainder",
                        "milestone_label": "",
                    }
                )
        else:
            periods.append(
                {
                    "key": quarter_label,
                    "label": quarter_label,
                    "start": current,
                    "end": quarter_end,
                    "kind": "quarter",
                    "milestone_label": "",
                }
            )

        current = _next_quarter(current)

    return periods


def _build_evolution_series(
    proposal_timelines: List[List[Dict[str, Any]]],
    periods: List[Dict[str, Any]],
    ordered_categories: List[str],
    *,
    standard_filter: str | None = None,
) -> Dict[str, Any]:
    counts_by_period = {period["key"]: Counter() for period in periods}
    bips_by_period = {period["key"]: defaultdict(set) for period in periods}

    for timeline in proposal_timelines:
        event_index = 0
        active_status = None
        active_standard = None
        proposal_id = timeline[0]["proposal_id"]

        for period in periods:
            period_end = period["end"]

            while event_index < len(timeline) and timeline[event_index]["date"] <= period_end:
                active_status = timeline[event_index]["status"]
                active_standard = timeline[event_index]["standard"]
                event_index += 1

            if not active_status:
                continue

            effective_standard = active_standard or _resolve_event_standard(None, period_end, active_status)

            if standard_filter is not None and effective_standard != standard_filter:
                continue

            period_key = period["key"]
            counts_by_period[period_key][active_status] += 1
            bips_by_period[period_key][active_status].add(proposal_id)

    rows = []
    for period in periods:
        period_key = period["key"]
        period_label = period["label"]
        values = {status: counts_by_period[period_key].get(status, 0) for status in ordered_categories}
        bips = {
            status: sorted(
                bips_by_period[period_key].get(status, set()),
                key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value),
            )
            for status in ordered_categories
        }
        rows.append(
            {
                "period": period_label,
                "period_key": period_key,
                "period_start": period["start"].isoformat(),
                "period_end": period["end"].isoformat(),
                "period_kind": period["kind"],
                "milestone_label": period.get("milestone_label", ""),
                "values": values,
                "bips": bips,
            }
        )

    return {
        "categories": ordered_categories,
        "rows": rows,
    }


def _order_statuses_for_standard(statuses: List[str], standard: str) -> List[str]:
    primary_order = BIP2_PRIMARY_STATUS_ORDER if standard == "bip2" else BIP3_PRIMARY_STATUS_ORDER
    remaining = sorted(status for status in statuses if status not in primary_order)
    return [status for status in primary_order if status in statuses] + remaining


def _build_segmented_evolution_series(
    series_by_standard: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    segment_definitions: List[Dict[str, str]] = []
    categories: List[str] = []

    for standard in ("bip2", "bip3"):
        counter = Counter()
        for row in series_by_standard.get(standard, {}).get("rows", []):
            for status, value in (row.get("values") or {}).items():
                counter[status] += int(value or 0)

        ordered_statuses = _order_statuses_for_standard(
            [status for status, total in counter.items() if total > 0],
            standard,
        )
        for status in ordered_statuses:
            key = f"{standard}:{status}"
            categories.append(key)
            segment_definitions.append(
                {
                    "key": key,
                    "status": status,
                    "standard": standard,
                    "label": status,
                }
            )

    base_rows = series_by_standard.get("bip2", {}).get("rows") or series_by_standard.get("bip3", {}).get("rows") or []
    rows = []

    for index, base_row in enumerate(base_rows):
        values = {}
        bips = {}

        for segment in segment_definitions:
            standard = segment["standard"]
            status = segment["status"]
            source_rows = series_by_standard.get(standard, {}).get("rows", [])
            source_row = source_rows[index] if index < len(source_rows) else {}
            values[segment["key"]] = int((source_row.get("values") or {}).get(status, 0) or 0)
            bips[segment["key"]] = list((source_row.get("bips") or {}).get(status, []))

        rows.append(
            {
                "period": base_row.get("period"),
                "period_key": base_row.get("period_key"),
                "period_start": base_row.get("period_start"),
                "period_end": base_row.get("period_end"),
                "period_kind": base_row.get("period_kind"),
                "milestone_label": base_row.get("milestone_label", ""),
                "values": values,
                "bips": bips,
            }
        )

    return {
        "categories": categories,
        "segmentDefinitions": segment_definitions,
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
        raw_timeline = get_changes_in_status(proposal)

        timeline = []
        for event in raw_timeline if isinstance(raw_timeline, list) else []:
            event_date = _parse_event_date(event.get("date") or event.get("timestamp"))
            status = _normalize_status(event.get("status"))
            if event_date is None or not status or not proposal_id:
                continue
            standard = _resolve_event_standard(
                event.get("standard"),
                event_date,
                status,
            )
            timeline.append(
                {
                    "proposal_id": proposal_id,
                    "date": event_date,
                    "status": status,
                    "standard": standard,
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
                "first_period": None,
                "last_period": None,
                "milestones": [],
            },
            "status_evolution": {
                "categories": [],
                "rows": [],
            },
            "status_evolution_segmented": {
                "categories": [],
                "segmentDefinitions": [],
                "rows": [],
            },
            "status_evolution_by_standard": {
                "bip2": {"categories": [], "rows": []},
                "bip3": {"categories": [], "rows": []},
            },
        }

    bip3_start_date = _resolve_bip3_start_date()
    ordered_categories = _build_status_order(list(category_set))
    periods = _build_periods(min_date, max_date, breakpoint_date=bip3_start_date)
    first_period = periods[0]
    last_period = periods[-1]
    ordered_categories_by_standard = {
        "bip2": _order_statuses_for_standard(list(category_set), "bip2"),
        "bip3": _order_statuses_for_standard(list(category_set), "bip3"),
    }

    proposal_ids = {
        _normalize_proposal_id(proposal.get("raw", {}).get("preamble", {}).get(id_field))
        for proposal in proposal_data
        if proposal.get("raw", {}).get("preamble", {}).get(id_field) is not None
    }

    status_evolution = _build_evolution_series(
        proposal_timelines,
        periods,
        ordered_categories,
    )
    status_evolution_by_standard = {
        "bip2": _build_evolution_series(
            proposal_timelines,
            periods,
            ordered_categories_by_standard["bip2"],
            standard_filter="bip2",
        ),
        "bip3": _build_evolution_series(
            proposal_timelines,
            periods,
            ordered_categories_by_standard["bip3"],
            standard_filter="bip3",
        ),
    }

    return {
        "meta": {
            "proposal_count": len(proposal_ids),
            "timeline_count": len(proposal_timelines),
            "first_year": first_period["start"].year,
            "last_year": last_period["end"].year,
            "first_period": first_period["label"],
            "last_period": last_period["label"],
            "milestones": [
                {
                    "date": bip3_start_date.isoformat(),
                    "label": "BIP3 Activation",
                }
            ] if bip3_start_date is not None else [],
        },
        "status_evolution": status_evolution,
        "status_evolution_segmented": _build_segmented_evolution_series(status_evolution_by_standard),
        "status_evolution_by_standard": status_evolution_by_standard,
    }
