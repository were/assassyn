"""Unit tests for assassyn.utils module.

This test suite validates utility functions in the assassyn.utils module.
"""

import assassyn


def test_has_verilator():
    """Test that has_verilator() returns a valid result.

    This test verifies that the has_verilator() function:
    - Returns None if Verilator or pycde is not available
    - Returns 'verilator' string if both are available
    - Does not raise exceptions
    """
    result = assassyn.utils.has_verilator()

    # The function should return either None or 'verilator' string
    assert result is None or result == 'verilator', \
        f"has_verilator() should return None or 'verilator', got {result}"

    # In this repository with proper setup, it should return 'verilator'
    # This assertion verifies the environment is properly configured
    assert result == 'verilator', \
        "has_verilator() should return 'verilator' in properly configured environment"
