"""Live Studionet consensus proof; opt in with QUORUM_LIVE=1."""
import os

import pytest

from scripts.demo import LiveDemo


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get('QUORUM_LIVE') != '1', reason='set QUORUM_LIVE=1 to deploy and run the live consensus demo'),
]


def test_live_studionet_adjudication_and_consumer_unlock():
    state = LiveDemo().execute()
    real_case = state['readbacks']['real_source_case']
    if real_case['consensus_status'] == 'UNDETERMINED':
        assert real_case['decision_persisted'] is False
        assert real_case['retry_performed'] is False
    else:
        assert real_case['consensus_status'] == 'ACCEPTED'
        assert real_case['qualified'] is False
    assert state['readbacks']['below_threshold']['count'] == 1
    assert state['readbacks']['above_threshold']['count'] == 2
    assert state['readbacks']['consumer_unlocked']['unlocked'] is True
