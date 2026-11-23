import base64
import hashlib
import json
from pathlib import Path

import pytest


CLAIM = 'Gauge A exceeded 4.0 metres at North Pier on 12 May.'


TEXTS = {
    'A': "AUTHORED TEST MATERIAL. Fictional report: Mira Chen said, 'I calibrated Gauge A and read 4.2 metres at North Pier on 12 May.'",
    'B': 'AUTHORED TEST MATERIAL. A rewritten account credits document A for Mira Chen\'s 4.2 metre Gauge A reading at North Pier on 12 May.',
    'C': 'AUTHORED TEST MATERIAL. This retelling repeats B and traces the 4.2 metre Gauge A observation at North Pier on 12 May to A.',
    'D': 'AUTHORED TEST MATERIAL. We are the Delta team; we separately calibrated Gauge A and recorded 4.1 metres at North Pier on 12 May. The Mira Chen report from A is background only.',
    'D_UNATTRIBUTED': 'AUTHORED TEST MATERIAL. Gauge A was said to be 4.1 metres at North Pier on 12 May.',
    'D_WRONG_DAY': 'AUTHORED TEST MATERIAL. The Delta team independently read Gauge A at 4.1 metres at North Pier on 13 May.',
    'D_SAME_LOG': 'AUTHORED TEST MATERIAL. A second article quotes the same instrument log attributed to Mira Chen: Gauge A read 4.2 metres at North Pier on 12 May.',
}


def document(doc_id, variant=None):
    key = variant or doc_id
    text = TEXTS[key]
    origin_candidates = [{'origin_id': 'origin_mira', 'description': 'Mira Chen, observer named in document A.'}]
    if key == 'D':
        origin_candidates.append({'origin_id': 'origin_delta', 'description': 'Delta team members reporting their own calibrated measurement.'})
    elif key in ('D_UNATTRIBUTED', 'D_WRONG_DAY'):
        origin_candidates.append({'origin_id': 'origin_delta', 'description': 'Delta team members reporting their own calibrated measurement.'})
    return {
        'doc_id': doc_id,
        'passage_id': 'p-' + doc_id.lower(),
        'source_mode': 'FIXTURE',
        'source_ref': 'fixture://quorum-of-sources/authored/' + key.lower(),
        'content_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
        'attribution': 'Authored fictional test material by the Quorum of Sources fixture author.',
        'passage': text,
        'source_text': text,
        'origin_candidates': origin_candidates,
    }


def row(doc_id, claim_supports, first_hand, origin_id, claim_quote='', origin_quote=''):
    return {
        'doc_id': doc_id,
        'passage_id': 'p-' + doc_id.lower(),
        'claim_supports': claim_supports,
        'first_hand': first_hand,
        'origin_id': origin_id,
        'claim_quote': claim_quote,
        'origin_quote': origin_quote,
        'reasoning': 'Mocked direct-mode decision.',
    }


ROWS_ABC = [
    row('A', True, True, 'origin_mira', '4.2 metres at North Pier on 12 May', 'I calibrated Gauge A and read 4.2 metres'),
    row('B', True, False, 'origin_mira', '4.2 metre Gauge A reading at North Pier on 12 May', 'credits document A'),
    row('C', True, False, 'origin_mira', '4.2 metre Gauge A observation at North Pier on 12 May', 'traces the 4.2 metre Gauge A observation'),
]


def rows_with_d(variant='D'):
    rows = list(ROWS_ABC)
    if variant == 'D':
        rows.append(row('D', True, True, 'origin_delta', 'recorded 4.1 metres at North Pier on 12 May', 'we separately calibrated Gauge A and recorded 4.1 metres'))
    elif variant == 'D_UNATTRIBUTED':
        rows.append(row('D', True, False, 'unknown'))
    elif variant == 'D_WRONG_DAY':
        rows.append(row('D', False, True, 'origin_delta'))
    else:
        rows.append(row('D', True, False, 'origin_mira'))
    return rows


def mock_rows(direct_vm, monkeypatch, rows):
    direct_vm.clear_mocks()
    direct_vm.mock_llm('QUORUM_OF_SOURCES', json.dumps({'documents': rows}))
    import genlayer.gl as sdk

    def run(leader_fn, validator_fn):
        result = leader_fn()
        assert validator_fn(sdk.vm.Return(result))
        return result

    monkeypatch.setattr(sdk.vm, 'run_nondet_unsafe', run)


def deploy_registry(direct_vm, direct_deploy, direct_owner):
    direct_vm.sender = direct_owner
    direct_vm._chain_id = 61999
    return direct_deploy('contracts/quorum_registry.py', 'gauge-demo', CLAIM)


def append(registry, direct_vm, direct_owner, doc_id, variant=None):
    direct_vm.sender = direct_owner
    payload = json.dumps(document(doc_id, variant), sort_keys=True, separators=(',', ':')).encode('utf-8')
    registry.append_document('gauge-demo', base64.b64encode(payload).decode('ascii'))


def test_authored_demo_counts_one_then_two_and_preserves_history(direct_vm, direct_deploy, direct_owner, monkeypatch):
    registry = deploy_registry(direct_vm, direct_deploy, direct_owner)
    for doc_id in ('A', 'B', 'C'):
        append(registry, direct_vm, direct_owner, doc_id)
    mock_rows(direct_vm, monkeypatch, ROWS_ABC)
    below = json.loads(registry.adjudicate('gauge-demo'))
    assert below['count'] == 1
    assert below['qualified'] is False
    first_revision = below['revision_id']

    append(registry, direct_vm, direct_owner, 'D')
    mock_rows(direct_vm, monkeypatch, rows_with_d())
    above = json.loads(registry.adjudicate('gauge-demo'))
    assert above['count'] == 2
    assert above['qualified'] is True
    assert above['revision_id'] != first_revision
    assert json.loads(registry.get_revision('gauge-demo', first_revision))['count'] == 1
    assert json.loads(registry.get_revision_status('gauge-demo', first_revision))['is_current'] is False


@pytest.mark.parametrize('variant', ['D_UNATTRIBUTED', 'D_WRONG_DAY', 'D_SAME_LOG'])
def test_nonindependent_or_wrong_event_does_not_add_origin(direct_vm, direct_deploy, direct_owner, monkeypatch, variant):
    registry = deploy_registry(direct_vm, direct_deploy, direct_owner)
    for doc_id in ('A', 'B', 'C'):
        append(registry, direct_vm, direct_owner, doc_id)
    append(registry, direct_vm, direct_owner, 'D', variant)
    mock_rows(direct_vm, monkeypatch, rows_with_d(variant))
    decision = json.loads(registry.adjudicate('gauge-demo'))
    assert decision['count'] == 1
    assert decision['qualified'] is False


def test_duplicate_document_and_duplicate_digest_are_rejected(direct_vm, direct_deploy, direct_owner):
    registry = deploy_registry(direct_vm, direct_deploy, direct_owner)
    append(registry, direct_vm, direct_owner, 'A')
    with direct_vm.expect_revert('duplicate document id'):
        append(registry, direct_vm, direct_owner, 'A')
    duplicate = document('A-copy', 'A')
    duplicate['doc_id'] = 'A-copy'
    duplicate['passage_id'] = 'p-a-copy'
    duplicate['source_ref'] = 'fixture://quorum-of-sources/authored/a-copy'
    with direct_vm.expect_revert('duplicate document content digest'):
        direct_vm.sender = direct_owner
        payload = json.dumps(duplicate, sort_keys=True, separators=(',', ':')).encode('utf-8')
        registry.append_document('gauge-demo', base64.b64encode(payload).decode('ascii'))


def test_reordered_append_keeps_manifest_and_revision_order_stable(direct_vm, direct_deploy, direct_owner, monkeypatch):
    registry = deploy_registry(direct_vm, direct_deploy, direct_owner)
    for doc_id in ('C', 'A', 'B'):
        append(registry, direct_vm, direct_owner, doc_id)
    mock_rows(direct_vm, monkeypatch, ROWS_ABC)
    decision = json.loads(registry.adjudicate('gauge-demo'))
    assert [item['doc_id'] for item in decision['evidence_manifest']] == ['A', 'B', 'C']
    expected_body = {
        'case_id': 'gauge-demo',
        'claim_sha256': hashlib.sha256(CLAIM.encode('utf-8')).hexdigest(),
        'documents': decision['evidence_manifest'],
    }
    expected_manifest = hashlib.sha256(json.dumps(expected_body, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    assert decision['manifest_sha256'] == expected_manifest


class RemoteView:
    def __init__(self, status):
        self.status = status

    def view(self):
        return self

    def get_revision_status(self, case_id, revision_id):
        return json.dumps(self.status)


def consumer_status(revision='rev-current', qualified=True, count=2, is_current=True, case_id='gauge-demo', claim=CLAIM):
    return {
        'case_id': case_id,
        'claim_sha256': hashlib.sha256(claim.encode('utf-8')).hexdigest(),
        'revision_id': revision,
        'threshold': 2,
        'count': count,
        'qualified': qualified,
        'is_current': is_current,
    }


def test_consumer_unlocks_once_from_current_registry_decision(direct_vm, direct_deploy, direct_owner, monkeypatch):
    remote = RemoteView(consumer_status())
    direct_vm.sender = direct_owner
    from gltest.direct.sdk_loader import setup_sdk_paths
    setup_sdk_paths(Path('contracts/quorum_consumer.py'))
    from genlayer.py.types import Address
    consumer = direct_deploy('contracts/quorum_consumer.py', Address(direct_owner), 'gauge-demo', CLAIM)
    import genlayer.gl as sdk

    monkeypatch.setattr(sdk, 'get_contract_at', lambda address: remote)
    consumer.unlock('rev-current')
    assert consumer.get_entitlement()['unlocked'] is True
    with direct_vm.expect_revert('already unlocked'):
        consumer.unlock('rev-current')


@pytest.mark.parametrize('status,expected', [
    (consumer_status(is_current=False), 'revision is stale'),
    (consumer_status(qualified=False, count=1), 'threshold not met'),
    (consumer_status(case_id='another-case'), 'different case'),
    (consumer_status(claim='Gauge B reached 4.0 metres at North Pier on 12 May.'), 'different claim'),
])
def test_consumer_rejects_wrong_stale_or_incomplete_registry_decision(direct_vm, direct_deploy, direct_owner, monkeypatch, status, expected):
    direct_vm.sender = direct_owner
    from gltest.direct.sdk_loader import setup_sdk_paths
    setup_sdk_paths(Path('contracts/quorum_consumer.py'))
    from genlayer.py.types import Address
    consumer = direct_deploy('contracts/quorum_consumer.py', Address(direct_owner), 'gauge-demo', CLAIM)
    import genlayer.gl as sdk

    monkeypatch.setattr(sdk, 'get_contract_at', lambda address: RemoteView(status))
    with direct_vm.expect_revert(expected):
        consumer.unlock(status['revision_id'])
    assert consumer.get_entitlement()['unlocked'] is False
