"""Test boost::spsc_queue wrapper."""
import queue

import pytest

import httpstan.spsc_queue


def test_spsc_queue():
    """Test boost::spsc_queue wrapper."""
    spsc_queue = httpstan.spsc_queue.SPSCQueue(100)
    with pytest.raises(queue.Empty):
        spsc_queue.get_nowait()
    assert spsc_queue.to_capsule() is not None
