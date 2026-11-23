# Quorum of Sources

Quorum of Sources is a small GenLayer contract pair for answering one narrow question: **how many distinct first-hand evidence origins does this submitted record document for this exact claim?** It does not certify that a publisher is honest or that two origins never coordinated.

## Deployed StudioNet demo

Network: StudioNet, chain ID `61999`. Both direct contract pages were opened and checked on the Studio Explorer.

- Registry: [0x610CCe277eaca01145D0A56dB0100D21026aCEa1](https://explorer-studio.genlayer.com/address/0x610CCe277eaca01145D0A56dB0100D21026aCEa1)
- Consumer: [0x6B5ce09B9B81E8AE4803087A1AB3F65917Bfe775](https://explorer-studio.genlayer.com/address/0x6B5ce09B9B81E8AE4803087A1AB3F65917Bfe775)
- Pinned GenVM runner: `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`

The live authored fixture run reached accepted consensus at both revisions:

| Stage | Result | Explorer transaction |
| --- | --- | --- |
| A/B/C, with B and C tracing the report to A | 1 origin; below threshold | [below-threshold adjudication](https://explorer-studio.genlayer.com/tx/0xac5ab3480e2e4e4a0b89b7eeba321d2572530442ff965c16f985a47616faf43d) |
| Append D, a second team's claimed calibrated reading | 2 origins; above threshold | [above-threshold adjudication](https://explorer-studio.genlayer.com/tx/0xf69e0438a6c23899ecd07ddde0545fded5f9b2aeb8790dcce9182da5282ba801) |
| Consumer reads the current registry revision and unlocks once | `unlocked: true` | [consumer unlock](https://explorer-studio.genlayer.com/tx/0xd46b362c7d23ae45a671d779300b86bda597e61a263e214bc4d1e182f18b9ecb) |

The first revision remains inspectable and is marked stale after D (`is_current: false`). The consumer's initial on-chain readback was locked. Its Explorer history contains only deployment and the later accepted unlock call, so no consumer write occurred during the one-origin stage. Final readbacks and revision IDs are in [`proofs/proof_manifest.json`](proofs/proof_manifest.json).

### Real public-source case

The separate NASA Apollo 11 case used `FETCH` mode against the NASA-hosted Lunar Surface Journal, checked the target-network response digest and exact passage, and submitted one adjudication. The leader proposed one origin, but the finalized transaction was **UNDETERMINED**: 3 validators disagreed, 1 agreed, and 1 was idle. No decision was persisted and that same revision was not retried. The Explorer does not expose the disagreeing validators' individual rationales. The quoted crew transmission's status as first-hand support is a plausible ambiguity; a validator-side fetch or digest issue also cannot be ruled out from the receipt.

- [NASA consensus transaction](https://explorer-studio.genlayer.com/tx/0xf576cd8f73a32d04b82785ee948c79eb5c53c3f32092af7d5839771033d8152e)
- Receipt summary: [`proofs/receipts/adjudicate-apollo11-public-consensus.json`](proofs/receipts/adjudicate-apollo11-public-consensus.json)
- Raw CLI receipt: [`proofs/receipts/adjudicate-apollo11-public.txt`](proofs/receipts/adjudicate-apollo11-public.txt)

## Design

- `contracts/quorum_registry.py` freezes one claim per case, caps cases at 4 evidence documents, rejects duplicate IDs/references/digests, sorts the manifest for deterministic revision IDs, and preserves prior decisions.
- `FIXTURE` records are exact frozen text with a digest and quote checks. All A-D passages are explicitly authored fictional test material. The demo does not represent Gauge A measurements as real sources.
- `FETCH` records require HTTPS and verify the fetched raw body digest before checking a canonicalized exact passage.
- Validators classify each stable document and passage ID, identify a bounded candidate origin, and provide exact supporting quotes. Contract code rejects invalid rows and derives the unique qualifying-origin count. The model cannot set a count, threshold result, or entitlement.
- `contracts/quorum_consumer.py` is configured to one registry, case, and claim hash. It reads a specific revision from the registry and checks it is current and qualified before a one-time unlock.

## Validation and reproduction

Validated locally before deployment:

```powershell
python -m pytest tests/direct -q
genvm-lint check contracts/quorum_registry.py
genvm-lint check contracts/quorum_consumer.py
genvm-lint schema contracts/quorum_registry.py --json
genvm-lint schema contracts/quorum_consumer.py --json
```

The direct suite passed **11 tests**, including the unattributed paraphrase, wrong-day measurement, shared instrument log, duplicates, reordered evidence, stale revisions, wrong claim/case, below-threshold unlock rejection, and repeat unlock. Those direct tests mock model output. Both contract schemas validated: registry has 3 write and 4 view methods; consumer has 1 write and 1 view method.

The linter passed both deployed contracts. It emitted informational warning `I200` because its cache lists a newer runner; the online latest-version lookup was unavailable during the check. The deployed contracts remain pinned to the tested runner above. A runner change needs a fresh deployment and new live evidence.

For a new live run, use a GenLayer CLI `0.40+` entry point, select the configured `studionet` network and development account, and run once against fresh deployments. StudioNet v0.6 requires fee-aware CLI support; the demo checks chain ID and reads `sim_getFeeConfig` before submitting.

```powershell
$env:GENLAYER_CLI_ENTRY = 'C:\path\to\node_modules\genlayer\dist\index.js'
python scripts\demo.py
```

The opt-in integration test calls the same live demo and stops at its locked-consumer precondition on this already-unlocked deployment. It is gated by `QUORUM_LIVE=1`; run it only with fresh contracts/state. No mainnet, paid service, publication, or Portal submission was used.

## Handoff

See [`REVIEW_HANDOFF.md`](REVIEW_HANDOFF.md) for the independent review question, proof links, and the central assumption to challenge.
