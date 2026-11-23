# Independent higher-model review

## Review question

Does this contract safely certify only what the submitted record documents, and does it avoid counting repeated reporting as independent evidence?

## Start with the evidence

- [`proofs/proof_manifest.json`](proofs/proof_manifest.json): network, verified contract entries, transaction receipts, decisions, and final readbacks.
- Registry: [StudioNet Explorer contract page](https://explorer-studio.genlayer.com/address/0x610CCe277eaca01145D0A56dB0100D21026aCEa1).
- Consumer: [StudioNet Explorer contract page](https://explorer-studio.genlayer.com/address/0x6B5ce09B9B81E8AE4803087A1AB3F65917Bfe775).
- Accepted below-threshold decision: [A/B/C transaction](https://explorer-studio.genlayer.com/tx/0xac5ab3480e2e4e4a0b89b7eeba321d2572530442ff965c16f985a47616faf43d).
- Accepted above-threshold decision: [A/B/C/D transaction](https://explorer-studio.genlayer.com/tx/0xf69e0438a6c23899ecd07ddde0545fded5f9b2aeb8790dcce9182da5282ba801).
- Accepted consumer unlock: [unlock transaction](https://explorer-studio.genlayer.com/tx/0xd46b362c7d23ae45a671d779300b86bda597e61a263e214bc4d1e182f18b9ecb).
- Unresolved real-source case: [NASA transaction](https://explorer-studio.genlayer.com/tx/0xf576cd8f73a32d04b82785ee948c79eb5c53c3f32092af7d5839771033d8152e), with validator split and receipt summary at [`proofs/receipts/adjudicate-apollo11-public-consensus.json`](proofs/receipts/adjudicate-apollo11-public-consensus.json).

## Readiness assessment

This is a learned review lens, not official criteria or a promise of points.

### Technical readiness

- Registry and consumer are deployed on StudioNet, pinned to the tested runner, and direct address pages were verified.
- Both live fixture revisions finalized with accepted consensus; the current revision was read through the consumer and unlocked once.
- Direct-mode edge cases passed. The unresolved NASA case remains a clear live-consensus limitation, and the linter's newer-runner notice is recorded.

### Distinctiveness

- The nearest earlier mechanism is **Footnote**: validators judge whether public posts are backed by sources, with separate evidence/tone labels, rechecks, and appeals. Quorum of Sources shares source retrieval and quote grounding, but its core output is a code-derived count of distinct first-hand origins for one claim, consumed by a separate contract.
- The user's same-week projects **MatchRight**, **LabelDesk**, and **Recusal** use frozen semantic evidence, validator judgments, or revision-bound decisions for offer matching, dataset-label release, and conflict handling respectively. None of their documented core outcomes is this bounded source-origin count plus one-time consumer gate. Shared GenLayer patterns remain common rather than unique.
- This is a mechanism-level comparison from the local project briefs and READMEs, not a score prediction.

### Evidence readiness

- Separate, verified direct Explorer contract entries and the three accepted fixture transaction links are in the manifest.
- The A-D passages are author-created fixtures; their live consensus proves the bounded flow, not real-world measurement evidence.
- The real NASA fetch is preserved but unresolved. A public repository was not created and no Portal form was submitted, following the task's explicit restrictions.

## Checks already performed

- Direct tests: 11 passed, using mocked model outputs for the cases listed in the README.
- GenVM lint and schema validation passed for both deployed contracts.
- Lint emitted informational `I200` for a newer runner listed in its local cache; its online latest-version lookup was unavailable. The deployed source stays pinned to the tested runner.
- Both contracts were opened by direct address on the StudioNet Explorer; their deployment and call entries match the manifest.
- The live fixture adjudications and cross-contract consumer unlock reached accepted consensus and their readbacks match the recorded decisions.
- The NASA transaction finalized as `UNDETERMINED`. It was preserved, diagnosed only to the extent supported by the receipt, and not repeated.

## Most important assumption to challenge

The case creator supplies the bounded candidate-origin roster. Model review can map a passage to one of those candidates and assess its first-hand wording, but the contract cannot prove that two candidate IDs represent genuinely independent people or organizations. A creator might omit a shared origin, split one publisher into aliases, or make coordinated sources look separate. Assess whether the current product boundary and disclosures are enough, or whether the roster needs stronger provenance or human review before it can safely trigger a real entitlement.

## Review constraints

All A-D documents are authored fictional test material. The NASA public source is distinct and unresolved. Do not interpret the fixture outcome as a real-world measurement or the contract result as a general truth verdict. Contract source has not been changed since deployment; any proposed contract change requires design confirmation, a fresh deployment, and new live evidence.
