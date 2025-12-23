"""Unit tests for retry utilities"""

from unittest.mock import patch

import pytest

from b3quant.utils.retry import exponential_backoff_with_jitter, retry_with_backoff


class TestExponentialBackoffWithJitter:
    """Tests for exponential backoff calculation"""

    def test_first_attempt_range(self):
        """Test that first attempt delay is within expected range"""
        delay = exponential_backoff_with_jitter(attempt=0, base_delay=1.0, jitter=True)
        # First attempt: 0 to 1 second with jitter
        assert 0 <= delay <= 1.0

    def test_second_attempt_range(self):
        """Test that second attempt delay is within expected range"""
        delay = exponential_backoff_with_jitter(attempt=1, base_delay=1.0, jitter=True)
        # Second attempt: 0 to 2 seconds with jitter
        assert 0 <= delay <= 2.0

    def test_third_attempt_range(self):
        """Test that third attempt delay is within expected range"""
        delay = exponential_backoff_with_jitter(attempt=2, base_delay=1.0, jitter=True)
        # Third attempt: 0 to 4 seconds with jitter
        assert 0 <= delay <= 4.0

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay"""
        delay = exponential_backoff_with_jitter(
            attempt=10, base_delay=1.0, max_delay=10.0, jitter=True
        )
        # Even with large attempt number, should be capped
        assert 0 <= delay <= 10.0

    def test_without_jitter(self):
        """Test exponential backoff without jitter"""
        delay = exponential_backoff_with_jitter(attempt=2, base_delay=1.0, jitter=False)
        # Without jitter, should be exactly 2^2 = 4 seconds
        assert delay == 4.0

    def test_custom_base_delay(self):
        """Test with custom base delay"""
        delay = exponential_backoff_with_jitter(
            attempt=1, base_delay=2.0, jitter=False
        )
        # 2.0 * 2^1 = 4.0
        assert delay == 4.0

    def test_jitter_randomness(self):
        """Test that jitter produces different values"""
        delays = [
            exponential_backoff_with_jitter(attempt=2, base_delay=1.0, jitter=True)
            for _ in range(10)
        ]
        # With jitter, we should get some variation
        # (Not all values should be the same)
        assert len(set(delays)) > 1

    def test_zero_attempt(self):
        """Test with attempt=0 without jitter"""
        delay = exponential_backoff_with_jitter(attempt=0, base_delay=1.0, jitter=False)
        # 1.0 * 2^0 = 1.0
        assert delay == 1.0


class TestRetryWithBackoff:
    """Tests for retry decorator"""

    def test_successful_first_attempt(self):
        """Test that successful call on first attempt doesn't retry"""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def success_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self):
        """Test that function retries on failure"""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries"""

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()

    def test_specific_exception_handling(self):
        """Test that only specified exceptions trigger retry"""

        @retry_with_backoff(
            max_retries=3, base_delay=0.01, exceptions=(ValueError,)
        )
        def raises_type_error():
            raise TypeError("Not retryable")

        # TypeError should not be retried
        with pytest.raises(TypeError, match="Not retryable"):
            raises_type_error()

    def test_on_retry_callback(self):
        """Test that on_retry callback is called"""
        callback_calls = []

        def on_retry_fn(attempt, exception):
            callback_calls.append((attempt, str(exception)))

        call_count = 0

        @retry_with_backoff(
            max_retries=3, base_delay=0.01, on_retry=on_retry_fn
        )
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Failure {call_count}")
            return "success"

        result = fails_twice()
        assert result == "success"
        assert len(callback_calls) == 2
        assert callback_calls[0][0] == 0
        assert "Failure 1" in callback_calls[0][1]

    @patch("time.sleep")
    def test_backoff_delay_called(self, mock_sleep):
        """Test that sleep is called with exponential backoff"""

        @retry_with_backoff(max_retries=3, base_delay=1.0, jitter=False)
        def fails_twice():
            if mock_sleep.call_count < 2:
                raise ValueError("Fail")
            return "success"

        result = fails_twice()
        assert result == "success"

        # Should have called sleep twice (for 2 retries)
        assert mock_sleep.call_count == 2

        # First delay should be around 1.0 (2^0 * 1.0)
        # Second delay should be around 2.0 (2^1 * 1.0)
        # Note: with jitter=False, delays are exact
        call_args = [call.args[0] for call in mock_sleep.call_args_list]
        assert call_args[0] == 1.0
        assert call_args[1] == 2.0

    def test_preserves_function_metadata(self):
        """Test that decorator preserves function metadata"""

        @retry_with_backoff(max_retries=3)
        def documented_function():
            """This function has documentation"""
            return "result"

        assert documented_function.__doc__ == "This function has documentation"
        assert documented_function.__name__ == "documented_function"

    @patch("time.sleep")
    def test_jitter_variations(self, mock_sleep):
        """Test that jitter produces varied delays"""

        @retry_with_backoff(max_retries=3, base_delay=1.0, jitter=True)
        def fails_twice():
            if mock_sleep.call_count < 2:
                raise ValueError("Fail")
            return "success"

        result = fails_twice()
        assert result == "success"

        # Should have called sleep twice
        assert mock_sleep.call_count == 2

        # With jitter, delays should be between 0 and max
        call_args = [call.args[0] for call in mock_sleep.call_args_list]
        assert 0 <= call_args[0] <= 1.0
        assert 0 <= call_args[1] <= 2.0
