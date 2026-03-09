from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from .conftest import AnotherSampleTestEvent, SampleTestEvent


def test_given_subscriber_when_matching_event_published_then_handler_called(event_publisher, test_event):
    # Arrange
    handler = Mock()
    event_publisher.subscribe(SampleTestEvent, handler)

    # Act
    event_publisher.publish(test_event)

    # Assert
    handler.assert_called_once_with(test_event)


def test_given_multiple_subscribers_when_event_published_then_all_handlers_called(event_publisher, test_event):
    # Arrange
    handler1 = Mock()
    handler2 = Mock()
    handler3 = Mock()

    event_publisher.subscribe(SampleTestEvent, handler1)
    event_publisher.subscribe(SampleTestEvent, handler2)
    event_publisher.subscribe(SampleTestEvent, handler3)

    # Act
    event_publisher.publish(test_event)

    # Assert
    handler1.assert_called_once_with(test_event)
    handler2.assert_called_once_with(test_event)
    handler3.assert_called_once_with(test_event)


def test_given_subscribers_for_different_events_when_specific_event_published_then_only_matching_handlers_called(
    event_publisher, test_event
):
    """Test that only subscribers for the specific event type are called."""
    # Arrange
    test_event_handler = Mock()
    another_event_handler = Mock()

    event_publisher.subscribe(SampleTestEvent, test_event_handler)
    event_publisher.subscribe(AnotherSampleTestEvent, another_event_handler)

    # Act
    event_publisher.publish(test_event)

    # Assert
    test_event_handler.assert_called_once_with(test_event)
    another_event_handler.assert_not_called()


def test_given_subscribers_for_different_events_when_other_event_published_then_only_matching_handlers_called(
    event_publisher, another_test_event
):
    # Arrange
    test_event_handler = Mock()
    another_event_handler = Mock()

    event_publisher.subscribe(SampleTestEvent, test_event_handler)
    event_publisher.subscribe(AnotherSampleTestEvent, another_event_handler)

    # Act
    event_publisher.publish(another_test_event)

    # Assert
    test_event_handler.assert_not_called()
    another_event_handler.assert_called_once_with(another_test_event)


def test_given_no_subscribers_when_event_published_then_no_error_occurs(event_publisher, test_event):
    # Act & Assert
    event_publisher.publish(test_event)


def test_given_subscriber_registered_multiple_times_when_event_published_then_handler_called_multiple_times(
    event_publisher, test_event
):
    # Arrange
    handler = Mock()
    event_publisher.subscribe(SampleTestEvent, handler)
    event_publisher.subscribe(SampleTestEvent, handler)  # Same handler registered twice

    # Act
    event_publisher.publish(test_event)

    # Assert
    assert handler.call_count == 2
    handler.assert_called_with(test_event)


def test_given_multiple_events_of_same_type_when_published_sequentially_then_all_handled(
    event_publisher,
):
    # Arrange
    handler = Mock()
    event_publisher.subscribe(SampleTestEvent, handler)

    event1 = SampleTestEvent(uuid4(), datetime.now(), "first event")
    event2 = SampleTestEvent(uuid4(), datetime.now(), "second event")
    event3 = SampleTestEvent(uuid4(), datetime.now(), "third event")

    # Act
    event_publisher.publish(event1)
    event_publisher.publish(event2)
    event_publisher.publish(event3)

    # Assert
    assert handler.call_count == 3
    handler.assert_any_call(event1)
    handler.assert_any_call(event2)
    handler.assert_any_call(event3)


def test_given_event_published_when_no_handlers_exist_for_event_type_then_empty_list_handled_gracefully(
    event_publisher,
):
    # Arrange
    test_handler = Mock()
    event_publisher.subscribe(SampleTestEvent, test_handler)

    another_event = AnotherSampleTestEvent(uuid4(), datetime.now(), 100)

    # Act
    event_publisher.publish(another_event)

    # Assert
    test_handler.assert_not_called()


def test_given_handler_that_raises_exception_when_event_published_then_exception_propagated(
    event_publisher, test_event
):
    # Arrange
    def failing_handler(event):
        raise Exception("Handler failed")

    event_publisher.subscribe(SampleTestEvent, failing_handler)

    # Act & Assert
    with pytest.raises(Exception, match="Handler failed"):
        event_publisher.publish(test_event)
