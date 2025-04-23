import pytest

def run_tests():
    """Run pytest with default options"""
    return pytest.main([])

def run_tests_debug():
    """Run pytest with debugging enabled"""
    return pytest.main(["--no-header", "-v", "--pdb"])