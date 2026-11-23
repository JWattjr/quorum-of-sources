# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import hashlib
import json

from genlayer import *


def require(condition, message):
    if not condition:
        raise gl.vm.UserError('[EXPECTED] ' + message)


def sha256_text(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class QuorumConsumer(gl.Contract):
    registry: Address
    case_id: str
    expected_claim_sha256: str
    unlocked: bool
    unlocked_revision_id: str

    def __init__(self, registry_address: Address, case_id: str, expected_claim: str):
        require(type(case_id) is str and 1 <= len(case_id) <= 48, 'invalid bound case id')
        require(type(expected_claim) is str and 12 <= len(expected_claim) <= 280, 'invalid bound claim')
        self.registry = registry_address
        self.case_id = case_id
        self.expected_claim_sha256 = sha256_text(expected_claim)
        self.unlocked = False
        self.unlocked_revision_id = ''

    @gl.public.write
    def unlock(self, revision_id: str) -> None:
        require(not self.unlocked, 'test entitlement already unlocked')
        require(type(revision_id) is str and revision_id.startswith('rev-'), 'invalid revision id')
        registry = gl.get_contract_at(self.registry)
        decision = json.loads(registry.view().get_revision_status(self.case_id, revision_id))
        require(decision['case_id'] == self.case_id, 'registry decision is for a different case')
        require(decision['claim_sha256'] == self.expected_claim_sha256, 'registry decision is for a different claim')
        require(decision['revision_id'] == revision_id, 'registry returned a different revision')
        require(decision['is_current'] is True, 'registry revision is stale')
        require(decision['threshold'] == 2, 'registry threshold mismatch')
        require(decision['qualified'] is True and decision['count'] >= 2, 'evidence threshold not met')
        self.unlocked = True
        self.unlocked_revision_id = revision_id

    @gl.public.view
    def get_entitlement(self) -> dict:
        return {
            'case_id': self.case_id,
            'claim_sha256': self.expected_claim_sha256,
            'unlocked': self.unlocked,
            'revision_id': self.unlocked_revision_id,
        }
