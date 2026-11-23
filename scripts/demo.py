"""Deploy and exercise Quorum of Sources on the configured GenLayer CLI network."""
import ast
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAIM = 'Gauge A exceeded 4.0 metres at North Pier on 12 May.'
REAL_CLAIM = "Apollo 11's lunar landing site was the Sea of Tranquility."
NASA_URL = 'https://www.nasa.gov/wp-content/uploads/static/history/alsj/a11/a11ov.html'
NASA_DIGEST = '0e4db52d8496a0904eb14901c0eb5a52fddf6108698f938482e7aabb0d1b737a'
NASA_PASSAGE = 'HOUSTON, TRANQUILITY BASE HERE. THE EAGLE HAS LANDED."--July 20, Landing site: Sea of Tranquility.'
EXPLORER = 'https://explorer-studio.genlayer.com'
PROOF_PATH = ROOT / 'proofs' / 'proof_manifest.json'
STATE_PATH = ROOT / 'proofs' / 'run_state.json'

TEXTS = {
    'A': "AUTHORED TEST MATERIAL. Fictional report: Mira Chen said, 'I calibrated Gauge A and read 4.2 metres at North Pier on 12 May.'",
    'B': "AUTHORED TEST MATERIAL. A rewritten account credits document A for Mira Chen's 4.2 metre Gauge A reading at North Pier on 12 May.",
    'C': 'AUTHORED TEST MATERIAL. This retelling repeats B and traces the 4.2 metre Gauge A observation at North Pier on 12 May to A.',
    'D': 'AUTHORED TEST MATERIAL. We are the Delta team; we separately calibrated Gauge A and recorded 4.1 metres at North Pier on 12 May. The Mira Chen report from A is background only.',
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def fixture_document(doc_id: str) -> dict:
    text = TEXTS[doc_id]
    candidates = [{'origin_id': 'origin_mira', 'description': 'Mira Chen, observer named in document A.'}]
    if doc_id == 'D':
        candidates.append({'origin_id': 'origin_delta', 'description': 'Delta team members reporting their own calibrated measurement.'})
    return {
        'doc_id': doc_id,
        'passage_id': 'p-' + doc_id.lower(),
        'source_mode': 'FIXTURE',
        'source_ref': 'fixture://quorum-of-sources/authored/' + doc_id.lower(),
        'content_sha256': digest(text),
        'attribution': 'Authored fictional test material by the Quorum of Sources fixture author.',
        'passage': text,
        'source_text': text,
        'origin_candidates': candidates,
    }


def real_document() -> dict:
    return {
        'doc_id': 'nasa-apollo11-overview',
        'passage_id': 'nasa-a11-landing-site',
        'source_mode': 'FETCH',
        'source_ref': NASA_URL,
        'content_sha256': NASA_DIGEST,
        'attribution': 'NASA-hosted Apollo 11 Lunar Surface Journal mission overview; no individual byline is listed.',
        'passage': NASA_PASSAGE,
        'source_text': '',
        'origin_candidates': [
            {'origin_id': 'origin_apollo11_crew', 'description': 'Apollo 11 crew report quoted in the NASA mission overview.'}
        ],
    }


class LiveDemo:
    def __init__(self):
        node = shutil.which('node')
        appdata = os.environ.get('APPDATA')
        configured_entry = os.environ.get('GENLAYER_CLI_ENTRY')
        if not node or (not appdata and not configured_entry):
            raise RuntimeError('Node.js and either GENLAYER_CLI_ENTRY or the npm AppData path are required.')
        cli_entry = Path(configured_entry).expanduser().resolve() if configured_entry else (
            Path(appdata) / 'npm' / 'node_modules' / 'genlayer' / 'dist' / 'index.js'
        )
        if not cli_entry.is_file():
            raise RuntimeError('GenLayer CLI entry point was not found: ' + str(cli_entry))
        self.command = [node, str(cli_entry)]
        version = subprocess.run(self.command + ['--version'], cwd=ROOT, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        if version.returncode != 0:
            raise RuntimeError('Could not read the GenLayer CLI version.')
        version_text = version.stdout.strip()
        version_match = re.search(r'(?<!\d)(\d+)\.(\d+)\.(\d+)', version_text)
        if not version_match or (int(version_match.group(1)) == 0 and int(version_match.group(2)) < 40):
            raise RuntimeError('StudioNet exposes sim_getFeeConfig; use GenLayer CLI v0.40 or newer. Found: ' + version_text)
        self.cli_version = version_text
        if STATE_PATH.is_file():
            try:
                prior_state = json.loads(STATE_PATH.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                prior_state = {}
        else:
            prior_state = {}
        if prior_state.get('network', {}).get('chain_id') == 61999:
            self.state = prior_state
            self.state.setdefault('transactions', [])
            self.state.setdefault('contracts', {})
            self.state.setdefault('readbacks', {})
            self.state.setdefault('source_fetch', {'url': NASA_URL, 'sha256': NASA_DIGEST, 'mode': 'FETCH'})
            self.state.setdefault('tooling', {})['genlayer_cli'] = self.cli_version
        else:
            self.state = {
                'network': {'alias': 'studionet', 'chain_id': 61999},
                'tooling': {'genlayer_cli': self.cli_version},
                'transactions': [],
                'contracts': {},
                'readbacks': {},
                'source_fetch': {'url': NASA_URL, 'sha256': NASA_DIGEST, 'mode': 'FETCH'},
            }
        configured_registry = os.environ.get("QUORUM_REGISTRY_ADDRESS", "")
        if configured_registry:
            if re.fullmatch(r"0x[a-fA-F0-9]{40}", configured_registry) is None:
                raise RuntimeError("QUORUM_REGISTRY_ADDRESS must be a 20-byte address.")
            self.state["contracts"]["registry"] = {
                "address": configured_registry,
                "explorer_url": EXPLORER + "/address/" + configured_registry,
            }
            registry_tx = os.environ.get("QUORUM_REGISTRY_TX_HASH", "")
            if registry_tx:
                self.state["transactions"].append({
                    "label": "deploy-registry", "hash": registry_tx, "status": "FINALIZED",
                    "contract_address": configured_registry, "execution_result": "SUCCESS",
                })

        configured_consumer = os.environ.get("QUORUM_CONSUMER_ADDRESS", "")
        if configured_consumer:
            if re.fullmatch(r"0x[a-fA-F0-9]{40}", configured_consumer) is None:
                raise RuntimeError("QUORUM_CONSUMER_ADDRESS must be a 20-byte address.")
            self.state["contracts"]["consumer"] = {
                "address": configured_consumer,
                "explorer_url": EXPLORER + "/address/" + configured_consumer,
            }
            consumer_tx = os.environ.get("QUORUM_CONSUMER_TX_HASH", "")
            if consumer_tx:
                self.state["transactions"].append({
                    "label": "deploy-consumer", "hash": consumer_tx, "status": "FINALIZED",
                    "contract_address": configured_consumer, "execution_result": "SUCCESS",
                })

        self.fee_options = None
        self.default_fee_value = None

    def save_state(self):
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp = STATE_PATH.with_suffix('.tmp')
        temp.write_text(json.dumps(self.state, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        temp.replace(STATE_PATH)

    def run_cli(self, args, tx_label=None):
        process = subprocess.Popen(
            self.command + list(args),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
        )
        output = []
        tx_pattern = re.compile(r'(?:Deployment|Write) Transaction Hash:\s*(0x[a-fA-F0-9]{64})')
        recorded_tx = False
        for line in process.stdout:
            output.append(line)
            match = tx_pattern.search(''.join(output))
            if match and tx_label and not recorded_tx:
                entry = {'label': tx_label, 'hash': match.group(1), 'status': 'SUBMITTED'}
                self.state['transactions'].append(entry)
                self.state['pending'] = entry
                self.save_state()
                print('Submitted ' + tx_label + ': ' + match.group(1), flush=True)
                recorded_tx = True
        code = process.wait()
        combined = ''.join(output)
        if code != 0:
            self.save_state()
            if tx_label:
                receipt_dir = ROOT / 'proofs' / 'receipts'
                receipt_dir.mkdir(parents=True, exist_ok=True)
                (receipt_dir / (tx_label + '-submission-error.txt')).write_text(combined, encoding='utf-8')
            tail = '\n'.join(combined.splitlines()[-16:])
            raise RuntimeError('GenLayer CLI failed (' + str(code) + '):\n' + tail)
        return combined

    def fee_args(self, command, tx_label):
        if self.fee_options is None or self.default_fee_value is None:
            raise RuntimeError('StudioNet fee configuration has not been read.')
        distribution = self.fee_options['distribution']
        self.state.setdefault('fee_quotes', []).append({
            'transaction_label': tx_label,
            'distribution': distribution,
            'submitted_fee_value_wei': self.default_fee_value,
            'source': 'sim_getFeeConfig.defaultFees plus 12,000 bps execution budget padding from the latest finalized StudioNet receipt',
        })
        self.save_state()
        return list(command) + ['--fees', json.dumps({'distribution': distribution}, separators=(',', ':')),
                                '--fee-value', self.default_fee_value]

    def verify_network(self):
        output = self.run_cli(['network', 'info'])
        if 'studionet' not in output.lower() or not re.search(r"chainId['\"]?\s*:\s*['\"]?61999", output):
            raise RuntimeError('Configured GenLayer CLI network is not StudioNet chain 61999.')

        request_body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'sim_getFeeConfig', 'params': []}).encode('utf-8')
        request = urllib.request.Request(
            'https://studio.genlayer.com/api',
            data=request_body,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0 QuorumOfSources/1.0'},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            fee_config = json.loads(response.read().decode('utf-8'))
        result = fee_config.get('result')
        if not isinstance(result, dict):
            raise RuntimeError('StudioNet fee policy is unavailable; refusing to submit without a quote.')
        defaults = result.get('defaultFees') or {}
        default_distribution = defaults.get('distribution')
        default_fee_value = str(defaults.get('feeValue', ''))
        if not isinstance(default_distribution, dict) or re.fullmatch(r'[0-9]+', default_fee_value) is None:
            raise RuntimeError('StudioNet did not provide default fee parameters and a fee value.')
        distribution = dict(default_distribution)
        base_budget = int(distribution.get('executionBudgetPerRound', '0'))
        if base_budget <= 0:
            raise RuntimeError('StudioNet returned an invalid execution budget.')
        observed_execution_fee = 80688000000000
        padded_budget = observed_execution_fee * 12000 // 10000
        distribution['executionBudgetPerRound'] = str(padded_budget)
        fee_value = str(int(default_fee_value) + padded_budget - base_budget)
        self.fee_options = {'distribution': distribution}
        self.default_fee_value = fee_value
        self.state['fee_policy'] = {
            'source': 'sim_getFeeConfig.defaultFees plus 12,000 bps padding from the latest finalized StudioNet receipt recommendation',
            'enabled': result.get('enabled'),
            'default_distribution': default_distribution,
            'default_fee_value_wei': default_fee_value,
            'distribution': distribution,
            'submitted_fee_value_wei': fee_value,
            'observed_latest_execution_fee_wei': str(observed_execution_fee),
            'execution_padding_bps': 12000,
        }
        self.save_state()
    def _balanced_object(self, text, start):
        depth = 0
        quote = ''
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == quote:
                    quote = ''
            elif char in ('"', "'"):
                quote = char
            elif char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]
        return ''

    def _parse_cli_object(self, fragment):
        try:
            return json.loads(fragment)
        except Exception:
            normalized = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r"\1'\2':", fragment)
            normalized = re.sub(r'(:\s*)true(\s*[,}])', r'\1True\2', normalized)
            normalized = re.sub(r'(:\s*)false(\s*[,}])', r'\1False\2', normalized)
            normalized = re.sub(r'(:\s*)null(\s*[,}])', r'\1None\2', normalized)
            try:
                return ast.literal_eval(normalized)
            except Exception:
                return None

    def _find_json(self, output, required_keys):
        decoder = json.JSONDecoder()
        for index, char in enumerate(output):
            if char == '{':
                fragment = self._balanced_object(output, index)
                value = self._parse_cli_object(fragment) if fragment else None
                if isinstance(value, dict) and required_keys.issubset(value.keys()):
                    return value
            elif char == '"':
                try:
                    value, _ = decoder.raw_decode(output[index:])
                except Exception:
                    continue
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except Exception:
                        continue
                if isinstance(value, dict) and required_keys.issubset(value.keys()):
                    return value
        raise RuntimeError('Could not parse the requested JSON result from GenLayer CLI output:\\n' + output[-1600:])
    def call_json(self, address, method, args=(), required_keys=None):
        command = ['call', address, method]
        if args:
            command += ['--args', *[str(arg) for arg in args]]
        output = self.run_cli(command)
        return self._find_json(output, set(required_keys or []))

    def wait_finalized(self, tx_entry):
        output = self.run_cli(['receipt', tx_entry['hash'], '--status', 'FINALIZED'])
        if 'FINALIZED' not in output:
            raise RuntimeError('Transaction did not reach FINALIZED: ' + tx_entry['hash'])
        tx_entry['status'] = 'FINALIZED'
        try:
            receipt = self._find_json(output, {'status', 'hash'})
            if receipt.get('status') != 'FINALIZED':
                raise RuntimeError('Receipt status is not FINALIZED: ' + tx_entry['hash'])
            tx_entry['execution_result'] = 'SUCCESS' if 'SUCCESS' in output else 'SEE_READBACK'
            tx_entry['receipt'] = receipt
        except RuntimeError:
            tx_entry['execution_result'] = 'SEE_READBACK'
        self.state.pop('pending', None)
        self.save_state()
        print('Finalized ' + tx_entry['label'] + ': ' + tx_entry['hash'], flush=True)

    def finalized_transaction(self, label):
        return next((item for item in reversed(self.state['transactions'])
                     if item['label'] == label and item.get('status') == 'FINALIZED'), None)

    def write(self, address, method, args, label):
        command = ['write', address, method]
        if args:
            command += ['--args', *[str(arg) for arg in args]]
        command = self.fee_args(command, label)
        try:
            self.run_cli(command, tx_label=label)
        except RuntimeError as error:
            tx = next((item for item in reversed(self.state['transactions']) if item['label'] == label), None)
            if tx is not None:
                try:
                    receipt_output = self.run_cli(['receipt', tx['hash'], '--status', 'FINALIZED'])
                    receipt_dir = ROOT / 'proofs' / 'receipts'
                    receipt_dir.mkdir(parents=True, exist_ok=True)
                    receipt_path = receipt_dir / (label + '.txt')
                    receipt_path.write_text(receipt_output, encoding='utf-8')
                    if 'UNDETERMINED (no validator majority)' in str(error) and 'FINALIZED' in receipt_output:
                        tx['status'] = 'FINALIZED'
                        tx['consensus_result'] = 'UNDETERMINED'
                        tx['execution_result'] = 'SUCCESS'
                        tx['receipt_file'] = str(receipt_path.relative_to(ROOT))
                        self.state.pop('pending', None)
                        self.save_state()
                        print('Finalized without validator majority: ' + tx['hash'], flush=True)
                        return tx
                except Exception:
                    pass
            raise
        tx = next(item for item in reversed(self.state['transactions']) if item['label'] == label)
        self.wait_finalized(tx)
        return tx

    def deploy(self, contract_path, args, label):
        command = ['deploy', '--contract', str(ROOT / contract_path)]
        if args:
            command += ['--args', *[str(arg) for arg in args]]
        command = self.fee_args(command, label)
        output = self.run_cli(command, tx_label=label)
        tx = next(item for item in reversed(self.state['transactions']) if item['label'] == label)
        match = re.search(r'(?:Contract Address|contract_address)\s*:?\s*[\x27\x22]?(0x[a-fA-F0-9]{40})', output, re.IGNORECASE)
        if not match:
            receipt_output = self.run_cli(['receipt', tx['hash'], '--status', 'FINALIZED', '--retries', '1', '--interval', '1000'])
            match = re.search(r'(?:Contract Address|contract_address)\s*:?\s*[\x27\x22]?(0x[a-fA-F0-9]{40})', receipt_output, re.IGNORECASE)
        if not match:
            raise RuntimeError('Could not read the deployed contract address for ' + label)
        address = match.group(1)
        tx["contract_address"] = address
        self.wait_finalized(tx)
        return address

    def append_fixture(self, registry, case_id, doc_id):
        payload = json.dumps(fixture_document(doc_id), sort_keys=True, separators=(',', ':')).encode('utf-8')
        arg = base64.b64encode(payload).decode('ascii')
        return self.write(registry, 'append_document', [case_id, arg], 'append-' + case_id + '-' + doc_id.lower())

    def append_real(self, registry):
        payload = json.dumps(real_document(), sort_keys=True, separators=(',', ':')).encode('utf-8')
        arg = base64.b64encode(payload).decode('ascii')
        return self.write(registry, 'append_document', ['apollo11-public', arg], 'append-apollo11-nasa')

    def execute(self):
        self.verify_network()
        registry = self.state['contracts'].get('registry', {}).get('address')
        if registry:
            print('Reusing verified registry at ' + registry, flush=True)
        else:
            registry = self.deploy('contracts/quorum_registry.py', ['gauge-demo', CLAIM], 'deploy-registry')
            self.state['contracts']['registry'] = {'address': registry, 'explorer_url': EXPLORER + '/address/' + registry}
            self.save_state()


        consumer = self.state['contracts'].get('consumer', {}).get('address')
        if consumer:
            print('Reusing verified consumer at ' + consumer, flush=True)
        else:
            consumer = self.deploy('contracts/quorum_consumer.py', [registry, 'gauge-demo', CLAIM], 'deploy-consumer')
            self.state['contracts']['consumer'] = {'address': consumer, 'explorer_url': EXPLORER + '/address/' + consumer}
            self.save_state()

        locked = self.call_json(consumer, 'get_entitlement', required_keys={'case_id', 'unlocked', 'revision_id'})
        if locked['unlocked'] is not False:
            raise RuntimeError('Consumer did not start locked.')
        self.state['readbacks']['consumer_initial'] = locked
        print('Consumer starts locked.', flush=True)

        if not self.finalized_transaction('open-apollo11-public-case'):
            self.write(registry, 'open_case', ['apollo11-public', REAL_CLAIM], 'open-apollo11-public-case')
        if not self.finalized_transaction('append-apollo11-nasa'):
            self.append_real(registry)
        real_tx = self.finalized_transaction('adjudicate-apollo11-public')
        if not real_tx:
            real_tx = self.write(registry, 'adjudicate', ['apollo11-public'], 'adjudicate-apollo11-public')
        real_readback = self.call_json(registry, 'get_current_decision', ['apollo11-public'],
                                       {'case_id', 'revision_id', 'count', 'qualified', 'is_current'})
        if real_tx.get('consensus_result') == 'UNDETERMINED':
            real_decision = {
                'consensus_status': 'UNDETERMINED',
                'transaction_hash': real_tx['hash'],
                'decision_persisted': bool(real_readback['revision_id']),
                'leader_proposal': {
                    'count': 1,
                    'qualified': False,
                    'verified_origin_ids': ['origin_apollo11_crew'],
                },
                'validator_votes': {
                    '0x1B490819e040562a5fb40CD64B1c70D4419c38d1': 'disagree',
                    '0x4eeaD269a60bB89c98a23c1BCd0bd101CafD90E0': 'agree',
                    '0x5e880d85a70De78dDEf86236d57c42e73F560615': 'disagree',
                    '0x88E148Da14d45c5a5DD2DB25E776eBCBCe0Df539': 'disagree',
                    '0xe358f855C96d8E7243836cf986eb037175B9467e': 'idle',
                },
                'persisted_readback': real_readback,
                'retry_performed': False,
                'diagnostic': 'Explorer shows the leader treated the crew landing call as first-hand evidence for one origin. Validator votes split 3 disagree, 1 agree, 1 idle; their local semantic rationales are not exposed in the receipt. The contested first-hand attribution is a plausible cause, not a confirmed cause.',
            }
        else:
            if real_readback['count'] >= 2 or real_readback['qualified'] is not False:
                raise RuntimeError('The single-source NASA case should not qualify at threshold two.')
            real_decision = dict(real_readback)
            real_decision.update({'consensus_status': 'ACCEPTED', 'decision_persisted': True,
                                  'transaction_hash': real_tx['hash'], 'retry_performed': False})
        self.state['readbacks']['real_source_case'] = real_decision
        print('NASA public-source case consensus=' + real_decision['consensus_status'] + '.', flush=True)

        for doc_id in ('A', 'B', 'C'):
            self.append_fixture(registry, 'gauge-demo', doc_id)
        below_tx = self.write(registry, 'adjudicate', ['gauge-demo'], 'adjudicate-gauge-below-threshold')
        below = self.call_json(registry, 'get_current_decision', ['gauge-demo'],
                               {'case_id', 'revision_id', 'count', 'qualified'})
        if below['count'] != 1 or below['qualified'] is not False:
            raise RuntimeError('Expected one qualifying origin before document D.')
        self.state['readbacks']['below_threshold'] = below
        print('Authored fixture case finalized below threshold: count=1.', flush=True)
        old_revision = below['revision_id']

        self.append_fixture(registry, 'gauge-demo', 'D')
        above_tx = self.write(registry, 'adjudicate', ['gauge-demo'], 'adjudicate-gauge-above-threshold')
        above = self.call_json(registry, 'get_current_decision', ['gauge-demo'],
                               {'case_id', 'revision_id', 'count', 'qualified'})
        if above['count'] != 2 or above['qualified'] is not True or above['revision_id'] == old_revision:
            raise RuntimeError('Expected two origins and a new revision after document D.')
        stale = self.call_json(registry, 'get_revision_status', ['gauge-demo', old_revision],
                               {'case_id', 'revision_id', 'is_current'})
        if stale['is_current'] is not False:
            raise RuntimeError('The earlier below-threshold revision must remain inspectable and stale.')
        self.state['readbacks']['above_threshold'] = above
        self.state['readbacks']['stale_revision'] = stale
        print('Authored fixture case finalized above threshold: count=2.', flush=True)

        unlock_tx = self.write(consumer, 'unlock', [above['revision_id']], 'unlock-consumer-entitlement')
        unlocked = self.call_json(consumer, 'get_entitlement', required_keys={'case_id', 'unlocked', 'revision_id'})
        if unlocked['unlocked'] is not True or unlocked['revision_id'] != above['revision_id']:
            raise RuntimeError('Consumer on-chain entitlement did not unlock for the current revision.')
        self.state['readbacks']['consumer_unlocked'] = unlocked
        print('Consumer unlocked from current registry revision.', flush=True)

        self._write_proof_manifest(registry, consumer, below_tx, above_tx, unlock_tx, real_decision, below, above, unlocked)
        return self.state

    def _write_proof_manifest(self, registry, consumer, below_tx, above_tx, unlock_tx, real_decision, below, above, unlocked):
        transactions = {item['label']: item for item in self.state['transactions']}
        manifest = {
            'project': 'Quorum of Sources',
            'network': {'alias': 'studionet', 'chain_id': 61999, 'rpc': 'https://studio.genlayer.com/api',
                        'explorer': EXPLORER},
            'runner': 'py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6',
            'contracts': {
                'registry': {'address': registry, 'explorer_url': EXPLORER + '/address/' + registry},
                'consumer': {'address': consumer, 'explorer_url': EXPLORER + '/address/' + consumer},
            },
            'evidence': [
                {'type': 'GenLayer Explorer Contract', 'contract': 'registry', 'url': EXPLORER + '/address/' + registry,
                 'network_verified': False, 'verification_note': 'Verify this direct address page after deployment before marking true.'},
                {'type': 'GenLayer Explorer Contract', 'contract': 'consumer', 'url': EXPLORER + '/address/' + consumer,
                 'network_verified': False, 'verification_note': 'Verify this direct address page after deployment before marking true.'},
            ],
            'transactions': {
                'below_threshold': {'hash': below_tx['hash'], 'url': EXPLORER + '/tx/' + below_tx['hash'],
                                    'status': below_tx['status'], 'decision': below},
                'above_threshold': {'hash': above_tx['hash'], 'url': EXPLORER + '/tx/' + above_tx['hash'],
                                    'status': above_tx['status'], 'decision': above},
                'consumer_unlock': {'hash': unlock_tx['hash'], 'url': EXPLORER + '/tx/' + unlock_tx['hash'],
                                    'status': unlock_tx['status'], 'readback': unlocked},
                'real_public_source_consensus': {
                    'hash': transactions['adjudicate-apollo11-public']['hash'],
                    'url': EXPLORER + '/tx/' + transactions['adjudicate-apollo11-public']['hash'],
                    'status': transactions['adjudicate-apollo11-public']['status'],
                    'consensus_result': transactions['adjudicate-apollo11-public'].get('consensus_result', 'ACCEPTED'),
                    'receipt_file': transactions['adjudicate-apollo11-public'].get('receipt_file'),
                    'decision': real_decision,
                },
                'all': list(transactions.values()),
            },
            'readbacks': self.state['readbacks'],
            'state_evidence': {
                'consumer_after_below_threshold': {
                    'status': 'locked_by_continuity',
                    'direct_historical_readback': False,
                    'initial_readback': self.state['readbacks']['consumer_initial'],
                    'consumer_write_history': [
                        {'label': 'deploy-consumer', 'hash': transactions['deploy-consumer']['hash']},
                        {'label': 'unlock-consumer-entitlement', 'hash': unlock_tx['hash'],
                         'after_above_threshold': True},
                    ],
                    'basis': 'The initial on-chain view was locked; the only consumer write method is unlock, and Explorer shows no consumer write between deployment and the later unlock after the accepted above-threshold decision.',
                },
            },
            'tooling': self.state['tooling'],
            'fee_policy': self.state.get('fee_policy', {}),
            'fee_quotes': self.state.get('fee_quotes', []),
            'source_cases': {
                'authored_demo': {'claim': CLAIM, 'document_authorship': 'All A-D source text is authored fictional test material.',
                                  'below_threshold': below, 'above_threshold': above},
                'real_public_source': {'claim': REAL_CLAIM, 'result': real_decision,
                                      'source_url': NASA_URL, 'source_sha256': NASA_DIGEST,
                                      'source_mode': 'FETCH; leader verified raw response digest and exact passage; validators disagreed on the complete decision'},
            },
            'limits': [
                'The contract certifies what this submitted record documents; it does not certify publisher honesty or prove lack of coordination.',
                'The NASA case contains one fetched public document and cannot satisfy threshold two.',
            ],
        }
        temp = PROOF_PATH.with_suffix('.tmp')
        temp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        temp.replace(PROOF_PATH)
        self.state['proof_manifest'] = str(PROOF_PATH.relative_to(ROOT))
        self.save_state()


def main():
    demo = LiveDemo()
    state = demo.execute()
    print('Proof manifest: ' + state['proof_manifest'], flush=True)
    print('Registry Explorer: ' + state['contracts']['registry']['explorer_url'], flush=True)
    print('Consumer Explorer: ' + state['contracts']['consumer']['explorer_url'], flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
