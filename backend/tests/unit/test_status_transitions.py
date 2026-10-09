import pytest
from app.models.order import OrderStatus
from app.services.order_service import OrderService


def test_allowed_status_transitions():
    allowed = OrderService.ALLOWED_TRANSITIONS

    # Valid next steps
    assert OrderStatus.ACCEPTED in allowed[OrderStatus.PLACED]
    assert OrderStatus.CANCELLED in allowed[OrderStatus.PLACED]

    assert OrderStatus.PREPARING in allowed[OrderStatus.ACCEPTED]
    assert OrderStatus.CANCELLED in allowed[OrderStatus.ACCEPTED]

    assert OrderStatus.READY in allowed[OrderStatus.PREPARING]
    assert OrderStatus.COLLECTED in allowed[OrderStatus.READY]

    # Invalid transitions
    assert OrderStatus.CANCELLED not in allowed[OrderStatus.PREPARING]
    assert OrderStatus.CANCELLED not in allowed[OrderStatus.READY]
    assert OrderStatus.COLLECTED not in allowed[OrderStatus.PLACED]
    assert OrderStatus.PREPARING not in allowed[OrderStatus.READY]
