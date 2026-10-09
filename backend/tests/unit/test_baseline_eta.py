from app.services.baseline_eta_service import BaselineETAService


def test_baseline_eta_formula_math():
    station_loads = {"tawa": 6.0, "fryer": 2.0}
    own_items = {"tawa": 4.0, "fryer": 3.0}
    station_cooks = {"tawa": 2, "fryer": 1}

    # Tawa wait = 6.0 + (4.0 / 2) = 8.0
    # Fryer wait = 2.0 + (3.0 / 1) = 5.0
    # max = 8.0
    eta = BaselineETAService.calculate_eta(station_loads, own_items, station_cooks)

    assert eta.median == 8
    assert eta.low == 6   # floor(8 * 0.75)
    assert eta.high == 10 # ceil(8 * 1.25)
    assert eta.source == "baseline"
    assert eta.low <= eta.median <= eta.high


def test_baseline_eta_monotonic_bounds():
    # Test very small numbers
    station_loads = {"tea": 0.0}
    own_items = {"tea": 0.5}
    station_cooks = {"tea": 1}

    eta = BaselineETAService.calculate_eta(station_loads, own_items, station_cooks)
    assert eta.low >= 1
    assert eta.median >= 1
    assert eta.high >= 1
    assert eta.low <= eta.median <= eta.high


def test_baseline_eta_fallback_empty():
    eta = BaselineETAService.calculate_eta({}, {}, {})
    assert eta.low >= 1
    assert eta.median >= 1
    assert eta.high >= 1
    assert eta.low <= eta.median <= eta.high
