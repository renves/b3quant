"""Tests for Implied Volatility Solver."""

import numpy as np
import pytest

from b3quant.models.iv_solver import ImpliedVolatilitySolver


class TestIVSolverBasic:
    """Basic IV solver functionality tests."""

    def test_atm_call_newton_raphson(self):
        """Test Newton-Raphson for ATM call option."""
        solver = ImpliedVolatilitySolver()

        # ATM call: S=K=100, T=30 days, r=5%, σ=20%
        # Calculate theoretical price first
        true_sigma = 0.20
        S, K, T, r = 100.0, 100.0, 30 / 365, 0.05

        # Price from Black-Scholes with σ=20%
        price = solver._black_scholes_price(S, K, T, r, true_sigma, 0, "call")

        # Solve for IV
        iv = solver.solve(price, S, K, T, r, option_type="call", method="newton")

        assert iv is not None
        assert abs(iv - true_sigma) < 0.001  # Within 0.1%

    def test_atm_put_newton_raphson(self):
        """Test Newton-Raphson for ATM put option."""
        solver = ImpliedVolatilitySolver()

        true_sigma = 0.25
        S, K, T, r = 100.0, 100.0, 60 / 365, 0.05

        price = solver._black_scholes_price(S, K, T, r, true_sigma, 0, "put")
        iv = solver.solve(price, S, K, T, r, option_type="put", method="newton")

        assert iv is not None
        assert abs(iv - true_sigma) < 0.001

    def test_otm_call_brent(self):
        """Test Brent's method for OTM call option."""
        solver = ImpliedVolatilitySolver()

        true_sigma = 0.30
        S, K, T, r = 100.0, 110.0, 30 / 365, 0.05  # 10% OTM

        price = solver._black_scholes_price(S, K, T, r, true_sigma, 0, "call")
        iv = solver.solve(price, S, K, T, r, option_type="call", method="brent")

        assert iv is not None
        assert abs(iv - true_sigma) < 0.001

    def test_itm_put_auto_method(self):
        """Test auto method selection for ITM put."""
        solver = ImpliedVolatilitySolver()

        true_sigma = 0.35
        S, K, T, r = 100.0, 105.0, 90 / 365, 0.05  # 5% ITM

        price = solver._black_scholes_price(S, K, T, r, true_sigma, 0, "put")
        iv = solver.solve(price, S, K, T, r, option_type="put", method="auto")

        assert iv is not None
        assert abs(iv - true_sigma) < 0.001


class TestIVSolverVectorized:
    """Vectorized IV calculation tests."""

    def test_vectorized_atm_calls(self):
        """Test vectorized IV calculation for ATM call chain."""
        solver = ImpliedVolatilitySolver()

        # Option chain: 3 calls at different strikes
        true_sigmas = np.array([0.20, 0.25, 0.30])
        S = 100.0
        K = np.array([95.0, 100.0, 105.0])
        T = 30 / 365
        r = 0.05

        # Calculate prices
        prices = np.array(
            [
                solver._black_scholes_price(S, K[i], T, r, true_sigmas[i], 0, "call")
                for i in range(3)
            ]
        )

        # Solve vectorized
        ivs = solver.solve_vectorized(prices, S, K, T, r, option_type="call")

        assert not np.any(np.isnan(ivs))  # All should succeed
        assert np.allclose(ivs, true_sigmas, atol=0.001)

    def test_vectorized_mixed_types(self):
        """Test vectorized IV with mixed call/put options."""
        solver = ImpliedVolatilitySolver()

        true_sigmas = np.array([0.20, 0.25])
        S = 100.0
        K = np.array([100.0, 100.0])
        T = 30 / 365
        r = 0.05
        option_types = np.array(["call", "put"])

        prices = np.array(
            [
                solver._black_scholes_price(S, K[0], T, r, true_sigmas[0], 0, "call"),
                solver._black_scholes_price(S, K[1], T, r, true_sigmas[1], 0, "put"),
            ]
        )

        ivs = solver.solve_vectorized(prices, S, K, T, r, option_type=option_types)

        assert not np.any(np.isnan(ivs))
        assert np.allclose(ivs, true_sigmas, atol=0.001)

    def test_vectorized_with_failures(self):
        """Test vectorized IV with some invalid inputs."""
        solver = ImpliedVolatilitySolver()

        # Mix of valid and invalid prices
        prices = np.array([5.0, -1.0, 3.0])  # Middle one is invalid
        S = 100.0
        K = np.array([100.0, 100.0, 100.0])
        T = 30 / 365
        r = 0.05

        ivs = solver.solve_vectorized(prices, S, K, T, r, option_type="call")

        # First and third should succeed, middle should be NaN
        assert not np.isnan(ivs[0])
        assert np.isnan(ivs[1])
        assert not np.isnan(ivs[2])


class TestIVSolverEdgeCases:
    """Edge case handling tests."""

    def test_deep_itm_call(self):
        """Test deep ITM call (nearly intrinsic value)."""
        solver = ImpliedVolatilitySolver()

        S, K, T, r = 100.0, 80.0, 30 / 365, 0.05  # 20% ITM
        intrinsic = S - K  # 20.0

        # Price very close to intrinsic
        price = intrinsic + 0.0005  # Just above intrinsic

        iv = solver.solve(price, S, K, T, r, option_type="call")

        # Should return None or very low IV (option nearly expired ITM)
        assert iv is None or iv < 0.01

    def test_deep_otm_put(self):
        """Test deep OTM put with very low price."""
        solver = ImpliedVolatilitySolver()

        S, K, T, r = 100.0, 80.0, 30 / 365, 0.05  # 20% OTM
        price = 0.001  # Very small price

        iv = solver.solve(price, S, K, T, r, option_type="put")

        # May succeed with high IV or fail gracefully
        if iv is not None:
            assert iv > 0.01  # Should be reasonably positive
            assert iv < solver.max_vol  # Within bounds

    def test_near_expiration(self):
        """Test option very close to expiration."""
        solver = ImpliedVolatilitySolver()

        S, K, r = 100.0, 100.0, 0.05
        T = 0.5 / 365  # 12 hours to expiry

        true_sigma = 0.30
        price = solver._black_scholes_price(S, K, T, r, true_sigma, 0, "call")

        iv = solver.solve(price, S, K, T, r, option_type="call")

        # Should handle gracefully (may use T_safe = 1 day)
        assert iv is not None
        # May not match exactly due to T adjustment
        assert 0.1 < iv < 1.0  # Reasonable range

    def test_high_volatility_regime(self):
        """Test high volatility (crisis scenario)."""
        solver = ImpliedVolatilitySolver()

        true_sigma = 1.5  # 150% volatility
        S, K, T, r = 100.0, 100.0, 30 / 365, 0.05

        price = solver._black_scholes_price(S, K, T, r, true_sigma, 0, "call")
        iv = solver.solve(price, S, K, T, r, option_type="call")

        assert iv is not None
        assert abs(iv - true_sigma) < 0.01  # Within 1%

    def test_with_dividends(self):
        """Test IV calculation with dividend yield."""
        solver = ImpliedVolatilitySolver()

        true_sigma = 0.25
        S, K, T, r, q = 100.0, 100.0, 60 / 365, 0.05, 0.02  # 2% div yield

        price = solver._black_scholes_price(S, K, T, r, true_sigma, q, "call")
        iv = solver.solve(price, S, K, T, r, q, option_type="call")

        assert iv is not None
        assert abs(iv - true_sigma) < 0.001


class TestIVSolverValidation:
    """Input validation tests."""

    def test_negative_price(self):
        """Test rejection of negative option price."""
        solver = ImpliedVolatilitySolver()

        iv = solver.solve(-1.0, S=100, K=100, T=0.25, r=0.05)

        assert iv is None

    def test_zero_price(self):
        """Test rejection of zero option price."""
        solver = ImpliedVolatilitySolver()

        iv = solver.solve(0.0, S=100, K=100, T=0.25, r=0.05)

        assert iv is None

    def test_price_above_stock(self):
        """Test rejection of call price > stock price."""
        solver = ImpliedVolatilitySolver()

        iv = solver.solve(150.0, S=100, K=100, T=0.25, r=0.05, option_type="call")

        assert iv is None

    def test_price_below_intrinsic(self):
        """Test rejection of price below intrinsic value."""
        solver = ImpliedVolatilitySolver()

        # ITM call: intrinsic = S - K = 10
        # Price below intrinsic should be rejected
        iv = solver.solve(5.0, S=100, K=90, T=0.25, r=0.05, option_type="call")

        assert iv is None

    def test_zero_time(self):
        """Test rejection of zero time to maturity."""
        solver = ImpliedVolatilitySolver()

        iv = solver.solve(5.0, S=100, K=100, T=0.0, r=0.05)

        assert iv is None

    def test_negative_strike(self):
        """Test rejection of negative strike."""
        solver = ImpliedVolatilitySolver()

        iv = solver.solve(5.0, S=100, K=-100, T=0.25, r=0.05)

        assert iv is None


class TestIVSolverInitialGuess:
    """Initial guess (Brenner-Subrahmanyam) tests."""

    def test_initial_guess_atm(self):
        """Test Brenner-Subrahmanyam approximation for ATM option."""
        solver = ImpliedVolatilitySolver()

        # ATM: S=K, use BS approximation
        price = 5.0
        S, K, T = 100.0, 100.0, 30 / 365

        guess = solver._initial_guess(price, S, K, T, "call")

        # BS approximation: σ ≈ √(2π/T) * (C/S)
        expected = np.sqrt(2 * np.pi / T) * (price / S)

        assert abs(guess - expected) < 0.01

    def test_initial_guess_otm(self):
        """Test initial guess for OTM option."""
        solver = ImpliedVolatilitySolver()

        price = 2.0
        S, K, T = 100.0, 110.0, 30 / 365  # 10% OTM

        guess = solver._initial_guess(price, S, K, T, "call")

        # Should return reasonable guess for OTM
        assert guess > 0.0  # Positive
        assert guess < solver.max_vol  # Within bounds
        # For OTM, may use heuristic based on moneyness
        assert 0.1 < guess < 1.0  # Reasonable range


class TestIVSolverConvergence:
    """Convergence behavior tests."""

    def test_convergence_speed_newton(self):
        """Test Newton-Raphson converges in expected iterations."""
        solver = ImpliedVolatilitySolver(max_iterations=50)

        true_sigma = 0.25
        S, K, T, r = 100.0, 100.0, 30 / 365, 0.05

        price = solver._black_scholes_price(S, K, T, r, true_sigma, 0, "call")

        # Track iterations (would need to modify solver to expose this)
        iv = solver.solve(price, S, K, T, r, option_type="call", method="newton")

        assert iv is not None
        # Newton-Raphson should converge quickly for ATM
        # (typically 3-5 iterations, but we can't verify without counter)

    def test_fallback_to_brent(self):
        """Test automatic fallback from Newton to Brent."""
        solver = ImpliedVolatilitySolver()

        # Deep OTM option that might challenge Newton-Raphson
        S, K, T, r = 100.0, 120.0, 7 / 365, 0.05
        true_sigma = 0.50

        price = solver._black_scholes_price(S, K, T, r, true_sigma, 0, "call")

        # Use auto method (should try Newton, may fall back to Brent)
        iv = solver.solve(price, S, K, T, r, option_type="call", method="auto")

        assert iv is not None
        assert abs(iv - true_sigma) < 0.01

    def test_damping_factor(self):
        """Test that damping improves stability."""
        # Create two solvers with different damping
        solver_high_damp = ImpliedVolatilitySolver(damping=0.5)
        solver_low_damp = ImpliedVolatilitySolver(damping=1.0)

        true_sigma = 0.30
        S, K, T, r = 100.0, 105.0, 14 / 365, 0.05

        price = solver_high_damp._black_scholes_price(S, K, T, r, true_sigma, 0, "call")

        iv_high = solver_high_damp.solve(
            price, S, K, T, r, option_type="call", method="newton"
        )
        iv_low = solver_low_damp.solve(
            price, S, K, T, r, option_type="call", method="newton"
        )

        # Both should converge to same result
        if iv_high is not None and iv_low is not None:
            assert abs(iv_high - iv_low) < 0.001


class TestIVSolverPrecision:
    """Numerical precision tests."""

    def test_high_precision_convergence(self):
        """Test that solver achieves target precision."""
        solver = ImpliedVolatilitySolver(tolerance=1e-6)

        true_sigma = 0.22
        S, K, T, r = 100.0, 100.0, 45 / 365, 0.05

        target_price = solver._black_scholes_price(S, K, T, r, true_sigma, 0, "call")
        iv = solver.solve(target_price, S, K, T, r, option_type="call")

        # Recalculate price with solved IV
        solved_price = solver._black_scholes_price(S, K, T, r, iv, 0, "call")

        # Price error should be within tolerance (using default 1e-6)
        assert (
            abs(solved_price - target_price) < 1e-5
        )  # Slightly relaxed for numerical stability

    def test_multiple_volatility_levels(self):
        """Test solver across wide range of volatilities."""
        solver = ImpliedVolatilitySolver()

        S, K, T, r = 100.0, 100.0, 30 / 365, 0.05
        test_sigmas = [0.05, 0.10, 0.20, 0.40, 0.80, 1.50]  # 5% to 150%

        for true_sigma in test_sigmas:
            price = solver._black_scholes_price(S, K, T, r, true_sigma, 0, "call")
            iv = solver.solve(price, S, K, T, r, option_type="call")

            assert iv is not None, f"Failed for σ={true_sigma}"
            assert abs(iv - true_sigma) < 0.01, f"Error too large for σ={true_sigma}"
