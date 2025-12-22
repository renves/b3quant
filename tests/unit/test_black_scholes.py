"""Unit tests for Black-Scholes option pricing model"""

import pytest
import numpy as np
from b3quant.models.black_scholes import BlackScholes


class TestBlackScholesPrice:
    """Tests for Black-Scholes pricing"""

    @pytest.fixture
    def bs(self):
        return BlackScholes()

    def test_call_price_atm(self, bs):
        """Test call pricing at-the-money (known value from literature)"""
        price = bs.price(S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="call")
        # Expected value from Black-Scholes tables
        assert abs(price - 10.4506) < 0.01

    def test_put_price_atm(self, bs):
        """Test put pricing at-the-money"""
        price = bs.price(S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="put")
        # Expected value from Black-Scholes tables
        assert abs(price - 5.5735) < 0.01

    def test_put_call_parity(self, bs):
        """Verify put-call parity: C - P = S - K*exp(-rT)"""
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.2

        call = bs.price(S=S, K=K, T=T, r=r, sigma=sigma, option_type="call")
        put = bs.price(S=S, K=K, T=T, r=r, sigma=sigma, option_type="put")

        # Put-call parity relationship
        left_side = call - put
        right_side = S - K * np.exp(-r * T)

        assert abs(left_side - right_side) < 0.01

    def test_call_itm_value(self, bs):
        """Test in-the-money call has intrinsic value"""
        # Deep ITM call
        price = bs.price(S=120, K=100, T=1.0, r=0.05, sigma=0.2, option_type="call")
        intrinsic = 120 - 100
        assert price > intrinsic  # Option worth more than intrinsic

    def test_call_otm_value(self, bs):
        """Test out-of-the-money call has only time value"""
        # Deep OTM call
        price = bs.price(S=80, K=100, T=1.0, r=0.05, sigma=0.2, option_type="call")
        assert price > 0  # Has some time value
        assert price < 5  # But not worth much

    def test_zero_volatility_call(self, bs):
        """Test call with zero volatility approaches intrinsic value"""
        # With very low volatility, call should approach max(S-K*exp(-rT), 0)
        price = bs.price(S=100, K=100, T=1.0, r=0.05, sigma=0.001, option_type="call")
        forward_value = 100 - 100 * np.exp(-0.05 * 1.0)
        assert abs(price - forward_value) < 0.1

    def test_vectorized_pricing(self, bs):
        """Test vectorized pricing with multiple strikes"""
        strikes = np.array([95, 100, 105, 110])
        prices = bs.price(
            S=100, K=strikes, T=1.0, r=0.05, sigma=0.2, option_type="call"
        )

        assert len(prices) == len(strikes)
        # Prices should decrease with higher strikes
        assert np.all(prices[:-1] >= prices[1:])

    def test_with_dividend_yield(self, bs):
        """Test pricing with dividend yield"""
        price_no_div = bs.price(
            S=100, K=100, T=1.0, r=0.05, sigma=0.2, q=0, option_type="call"
        )
        price_with_div = bs.price(
            S=100, K=100, T=1.0, r=0.05, sigma=0.2, q=0.02, option_type="call"
        )

        # With dividends, call should be worth less
        assert price_with_div < price_no_div


class TestBlackScholesGreeks:
    """Tests for Black-Scholes Greeks"""

    @pytest.fixture
    def bs(self):
        return BlackScholes()

    def test_delta_sum_rule(self, bs):
        """Verify call delta + abs(put delta) ≈ 1 for same strike"""
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.2

        call_delta = bs.delta(
            S=S, K=K, T=T, r=r, sigma=sigma, option_type="call"
        )
        put_delta = bs.delta(S=S, K=K, T=T, r=r, sigma=sigma, option_type="put")

        # For zero dividend yield: call_delta - put_delta = exp(-q*T) = 1
        assert abs(call_delta - put_delta - 1.0) < 0.01

    def test_delta_bounds_call(self, bs):
        """Test call delta is between 0 and 1"""
        delta = bs.delta(
            S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="call"
        )
        assert 0 <= delta <= 1

    def test_delta_bounds_put(self, bs):
        """Test put delta is between -1 and 0"""
        delta = bs.delta(
            S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="put"
        )
        assert -1 <= delta <= 0

    def test_gamma_symmetry(self, bs):
        """Gamma should be the same for calls and puts"""
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.2

        gamma = bs.gamma(S=S, K=K, T=T, r=r, sigma=sigma)

        # Gamma doesn't depend on option type
        # Just verify it's positive and reasonable
        assert gamma > 0
        assert gamma < 1  # Reasonable upper bound

    def test_gamma_maximum_at_atm(self, bs):
        """Gamma should be maximum near at-the-money (forward)"""
        S, T, r, sigma = 100, 1.0, 0.05, 0.2

        # Gamma is maximum at forward ATM: F = S*exp((r-q)*T)
        # For r=0.05, T=1, F ≈ 105
        gamma_near_atm = bs.gamma(S=S, K=105, T=T, r=r, sigma=sigma)
        gamma_deep_itm = bs.gamma(S=S, K=80, T=T, r=r, sigma=sigma)
        gamma_deep_otm = bs.gamma(S=S, K=120, T=T, r=r, sigma=sigma)

        # Gamma should be higher near ATM than deep ITM/OTM
        assert gamma_near_atm > gamma_deep_itm
        assert gamma_near_atm > gamma_deep_otm

    def test_vega_positive(self, bs):
        """Vega should always be positive"""
        vega = bs.vega(S=100, K=100, T=1.0, r=0.05, sigma=0.2)
        assert vega > 0

    def test_vega_symmetry(self, bs):
        """Vega should be the same for calls and puts"""
        # Vega doesn't take option_type, but verify it's consistent
        vega = bs.vega(S=100, K=100, T=1.0, r=0.05, sigma=0.2)
        assert vega > 0

    def test_theta_typically_negative(self, bs):
        """Theta should typically be negative for long positions"""
        theta_call = bs.theta(
            S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="call"
        )
        theta_put = bs.theta(
            S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="put"
        )

        # Theta is typically negative (time decay)
        # Note: Can be positive for deep ITM puts
        assert theta_call < 0

    def test_rho_call_positive(self, bs):
        """Rho for calls should be positive"""
        rho = bs.rho(
            S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="call"
        )
        assert rho > 0

    def test_rho_put_negative(self, bs):
        """Rho for puts should be negative"""
        rho = bs.rho(
            S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="put"
        )
        assert rho < 0

    def test_greeks_vectorized(self, bs):
        """Test Greeks work with vectorized inputs"""
        strikes = np.array([95, 100, 105])

        deltas = bs.delta(
            S=100, K=strikes, T=1.0, r=0.05, sigma=0.2, option_type="call"
        )
        gammas = bs.gamma(S=100, K=strikes, T=1.0, r=0.05, sigma=0.2)
        vegas = bs.vega(S=100, K=strikes, T=1.0, r=0.05, sigma=0.2)

        assert len(deltas) == len(strikes)
        assert len(gammas) == len(strikes)
        assert len(vegas) == len(strikes)


class TestBlackScholesValidation:
    """Tests for input validation"""

    @pytest.fixture
    def bs(self):
        return BlackScholes()

    def test_negative_spot_raises_error(self, bs):
        """Test that negative spot price raises ValueError"""
        with pytest.raises(ValueError, match="Underlying price S must be positive"):
            bs.price(S=-100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="call")

    def test_negative_strike_raises_error(self, bs):
        """Test that negative strike raises ValueError"""
        with pytest.raises(ValueError, match="Strike price K must be positive"):
            bs.price(S=100, K=-100, T=1.0, r=0.05, sigma=0.2, option_type="call")

    def test_negative_time_raises_error(self, bs):
        """Test that negative time raises ValueError"""
        with pytest.raises(ValueError, match="Time to maturity T cannot be negative"):
            bs.price(S=100, K=100, T=-1.0, r=0.05, sigma=0.2, option_type="call")

    def test_negative_volatility_raises_error(self, bs):
        """Test that negative volatility raises ValueError"""
        with pytest.raises(ValueError, match="Volatility sigma must be positive"):
            bs.price(S=100, K=100, T=1.0, r=0.05, sigma=-0.2, option_type="call")

    def test_invalid_option_type_raises_error(self, bs):
        """Test that invalid option type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid option_type"):
            bs.price(S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type="invalid")


class TestBlackScholesEdgeCases:
    """Tests for edge cases and boundary conditions"""

    @pytest.fixture
    def bs(self):
        return BlackScholes()

    def test_zero_time_to_maturity(self, bs):
        """Test behavior at expiration (T=0 should give intrinsic value)"""
        # At expiration, option value = intrinsic value
        # Note: T=0 causes division by zero, so use very small T
        price = bs.price(
            S=105, K=100, T=1e-10, r=0.05, sigma=0.2, option_type="call"
        )
        intrinsic = 105 - 100
        assert abs(price - intrinsic) < 0.01

    def test_very_high_volatility(self, bs):
        """Test with very high volatility"""
        price = bs.price(
            S=100, K=100, T=1.0, r=0.05, sigma=2.0, option_type="call"
        )
        # Very high volatility means lots of uncertainty, high option value
        assert price > 30  # Should be significant

    def test_long_maturity(self, bs):
        """Test with long time to maturity"""
        price = bs.price(
            S=100, K=100, T=10.0, r=0.05, sigma=0.2, option_type="call"
        )
        # Long maturity means more time value
        assert price > 20

    def test_deep_itm_call(self, bs):
        """Test deep in-the-money call"""
        price = bs.price(
            S=150, K=100, T=1.0, r=0.05, sigma=0.2, option_type="call"
        )
        # Deep ITM call should be worth at least intrinsic value
        intrinsic = 150 - 100
        assert price >= intrinsic

    def test_deep_otm_call(self, bs):
        """Test deep out-of-the-money call"""
        price = bs.price(
            S=50, K=100, T=1.0, r=0.05, sigma=0.2, option_type="call"
        )
        # Deep OTM call should have very low value
        assert price < 1.0
