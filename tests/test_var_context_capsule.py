"""Test array_var_context capsules."""
import httpstan.stan


def test_array_var_context_capsule():
    """Test array_var_context capsule."""
    data = {"J": 3}
    array_var_context_capsule = httpstan.stan.make_array_var_context(data)
    assert httpstan.stan._array_var_context_contains("J", array_var_context_capsule)
    assert not httpstan.stan._array_var_context_contains("no-such-key", array_var_context_capsule)
