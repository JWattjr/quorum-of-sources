# Submission draft (not submitted)

## Note (under 1,000 characters)

Quorum of Sources is a two-contract protocol. A registry freezes one claim and a bounded list of candidate origins per source. Validators judge each source passage: does it support the claim, is it first-hand, and which candidate origin does it trace to? Reposts and retellings map to the same origin, so they do not add to the count. Code, not the model, counts distinct qualifying origins against a threshold of 2. A separate consumer contract reads the registry's current revision and unlocks a test entitlement once, rejecting stale or below-threshold revisions. Live on StudioNet: one origin (below threshold), then a second team's source (above threshold) and a consumer unlock. A real CPython source also finalized, counting zero because the passage is not positively first-hand. Fixtures are authored and fictional; the creator picks the candidate origins.

## Evidence entries

1. **GenLayer Explorer Contract, registry (StudioNet):** https://explorer-studio.genlayer.com/address/0x610CCe277eaca01145D0A56dB0100D21026aCEa1
2. **GenLayer Explorer Contract, consumer (StudioNet):** https://explorer-studio.genlayer.com/address/0x6B5ce09B9B81E8AE4803087A1AB3F65917Bfe775
3. **Source repository:** https://github.com/JWattjr/quorum-of-sources (both deployed contracts match the pushed files byte for byte)
4. **Below-threshold adjudication (1 origin):** https://explorer-studio.genlayer.com/tx/0xac5ab3480e2e4e4a0b89b7eeba321d2572530442ff965c16f985a47616faf43d
5. **Above-threshold adjudication (2 origins):** https://explorer-studio.genlayer.com/tx/0xf69e0438a6c23899ecd07ddde0545fded5f9b2aeb8790dcce9182da5282ba801
6. **Consumer unlock:** https://explorer-studio.genlayer.com/tx/0xd46b362c7d23ae45a671d779300b86bda597e61a263e214bc4d1e182f18b9ecb
7. **Real-source adjudication (CPython docs, finalized):** https://explorer-studio.genlayer.com/tx/0x7c466ad9b37e0413110784e760d308c64fdd4c5b96131e5003f2132c3fef4fe3

## Comparison with the author's same-week projects

| Project | What validators judge | What code does with it |
|---|---|---|
| matchright | Whether the incumbent's clause equals the outsider's | Assigns the entitlement, confirmed expiry defaults to the outsider |
| recusal | Whether disclosed conduct meets a frozen grant policy | Applies the date rule and the ballot roster |
| **quorum-of-sources** | Per source: claim support, first-hand, which candidate origin | Counts distinct qualifying origins; a second contract gates an unlock on the count |

The distinct part is counting independent origins (so repeated reporting adds nothing) and a cross-contract gate bound to one case, claim hash and current revision. Nearest earlier work is Footnote, which judges whether posts are backed by sources.

## This does not prove

That candidate origins are truly independent: the case creator supplies the roster. Real-world measurement (the A-D fixtures are authored and fictional). A positive quorum on real sources: the one real case finalized with zero counted. Adversarial validators, or any real asset gate. No Portal submission or score is claimed.
