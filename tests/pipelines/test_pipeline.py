from __future__ import annotations

from data.pipelines.pipeline import (
    aggregate_monthly_clinic_supply_metrics,
    validate_and_deduplicate_supply_events,
)


MONTH_START = "2026-07-01"


def event(event_id: str, event_type: str, timestamp: str, **properties: object) -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "timestamp": timestamp,
        "request_id": f"request-{event_id}",
        "tags": properties,
    }


def validated(events: list[dict[str, object]]) -> dict[str, object]:
    return validate_and_deduplicate_supply_events.fn(events, MONTH_START)


def test_validation_deduplicates_retried_supply_events() -> None:
    events = [
        event(
            "inbound-1",
            "inbound_order_created",
            "2026-07-03T09:00:00Z",
            clinic_id="austin-north",
            country="US",
            quantity=10,
            unit_cost=12.5,
        ),
        event(
            "inbound-1",
            "inbound_order_created",
            "2026-07-03T09:00:00Z",
            clinic_id="austin-north",
            country="US",
            quantity=10,
            unit_cost=12.5,
        ),
    ]

    result = validated(events)

    assert result["records_extracted"] == 2
    assert result["records_processed"] == 1
    assert result["records_rejected"] == 0


def test_supply_cost_and_consumption_kpis_match_hand_calculation() -> None:
    result = validated(
        [
            event(
                "inbound-1",
                "inbound_order_created",
                "2026-07-03T09:00:00Z",
                clinic_id="austin-north",
                country="US",
                quantity=10,
                unit_cost=12.5,
            ),
            event(
                "inbound-2",
                "inbound_order_created",
                "2026-07-08T09:00:00Z",
                clinic_id="austin-north",
                country="US",
                quantity=4,
                total_cost=100,
            ),
            event(
                "outbound-1",
                "outbound_order_created",
                "2026-07-09T09:00:00Z",
                clinic_id="austin-north",
                country="US",
                quantity=2,
                department="cardiology",
            ),
            event(
                "outbound-2",
                "outbound_order_created",
                "2026-07-10T09:00:00Z",
                clinic_id="austin-north",
                country="US",
                quantity=1,
                department="cardiology",
            ),
        ]
    )

    aggregate = aggregate_monthly_clinic_supply_metrics.fn(result, MONTH_START)
    row = aggregate["rows"][0]

    assert row["total_supply_cost"] == 225.0
    assert row["supply_consumption_count"] == 2
    assert aggregate["department_counts"] == [
        {"clinic_id": "austin-north", "department": "cardiology", "count": 2}
    ]


def test_stockout_and_expiry_kpis_are_grouped_by_clinic_and_country() -> None:
    result = validated(
        [
            event(
                "stockout-1",
                "stock_threshold_triggered",
                "2026-07-11T09:00:00Z",
                clinic_id="london-central",
                country="UK",
            ),
            event(
                "stockout-2",
                "stock_threshold_triggered",
                "2026-07-12T09:00:00Z",
                clinic_id="london-central",
                country="UK",
            ),
            event(
                "expiry-1",
                "supply_expiry_flagged",
                "2026-07-13T09:00:00Z",
                clinic_id="london-central",
                country="UK",
            ),
        ]
    )

    aggregate = aggregate_monthly_clinic_supply_metrics.fn(result, MONTH_START)
    row = aggregate["rows"][0]

    assert row["clinic_id"] == "london-central"
    assert row["country"] == "UK"
    assert row["critical_stockout_count"] == 2
    assert row["expiry_risk_count"] == 1
    assert row["currency"] == "GBP"


def test_malformed_event_is_rejected_without_losing_valid_kpis() -> None:
    result = validated(
        [
            event(
                "invalid-1",
                "inbound_order_created",
                "2026-07-14T09:00:00Z",
                clinic_id="austin-north",
                country="US",
                quantity=3,
            ),
            event(
                "valid-1",
                "supply_expiry_flagged",
                "2026-07-14T09:00:00Z",
                clinic_id="austin-north",
                country="US",
            ),
        ]
    )

    assert result["records_processed"] == 1
    assert result["records_rejected"] == 1
    assert result["rejection_codes"] == {"MISSING_SUPPLY_COST": 1}

    aggregate = aggregate_monthly_clinic_supply_metrics.fn(result, MONTH_START)
    assert aggregate["rows"][0]["expiry_risk_count"] == 1
