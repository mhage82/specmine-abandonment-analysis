# Abandonment Candidate Review

## Candidate A01: Web Console Config Diet

- Repository: modu-ai/moai-adk
- Record ID: 2fc98809ab7de370
- Specification: SPEC-WEB-CONSOLE-CONFIG-DIET-001


- Reviewer and review date: Jeremiah Briggs 10/26/26
- Concrete scope being evaluated: Removal or restriction of ineffective configuration options exposed by the web console, as described in SPEC-WEB-CONSOLE-CONFIG-DIET-001.
- Evidence actually inspected (URL/revision and relevant passage or code): .moai/specs/SPEC-WEB-CONSOLE-CONFIG-DIET-001/spec.md, revision 5e2d99469aba570a33886b6605063af445a4d0ef, from the uploaded specification snapshot. The frontmatter records status: cancelled. The HISTORY entry dated July 5, 2026 explains that a parallel rollback of WEB-CONSOLE-011 removed the expanded configuration interface, making this cleanup unnecessary.
- Your scope status and reasoning: Provisionally superseded. The document explicitly attributes cancellation to another change that removed the underlying problem. This supports supersession rather than abandonment under the proposed protocol.
- Supported event date and precision, or unknown: July 5, 2026, day-level precision, as recorded in the specification’s cancellation history. Not independently corroborated.
- Evidence of unfinished, ongoing work at a prediction date, or unknown: Unknown. The document reports approval to begin implementation before cancellation, but status at a defined prediction date has not been reconstructed.
- Observed follow-up end and evidence coverage, or unknown: Specification history collection timestamp: July 11, 2026, at 01:41:08 UTC. This does not establish complete coverage of implementation activity or discussions.
- Rename, replacement, scope change, or shared-outcome concerns: The recorded reason is supersession by the WEB-CONSOLE-011 rollback. Verify that rollback and its relationship to this specification.
- Agreement or disagreement with inherited decision: Not applicable to the earlier completion-review cohort. The source records cancellation; this review interprets its stated reason as supersession.
- Remaining evidence needed: Inspect the rollback commit and related decision record to corroborate the reason and date. Establish baseline eligibility before considering any training use.



## Candidate A02: Skill Fabric

- Repository: anton-abyzov/specweave-umb
- Record ID: 5bc7a1cfa507833d
- Specification: 0205-skill-fabric



- Reviewer and review date: Jeremiah Briggs 10/26/26
- Concrete scope being evaluated: Skill Fabric terminology and natural-language documentation, CLI skill discovery commands, and a curated skill registry with security validation and contributor trust tiers. 
- Evidence actually inspected (URL/revision and relevant passage or code): .specweave/increments/_archive/0205-skill-fabric/spec.md, supplied specification text. The frontmatter explicitly records status: abandoned. All nine acceptance criteria are unchecked. The supplied text contains no abandonment date or explanation. 
- Your scope status and reasoning: Source-declared abandoned; final classification pending. The specification explicitly records abandonment, but the extent of implementation and any continuation under another specification remain unresolved. 
- Supported event date and precision, or unknown: Unknown. No abandonment date appears in the supplied text. 
- Evidence of unfinished, ongoing work at a prediction date, or unknown: Unknown. The unchecked criteria do not establish historical status at a prediction date. 
- Observed follow-up end and evidence coverage, or unknown: Unknown. This review covers the supplied specification text only. 
- Rename, replacement, scope change, or shared-outcome concerns: An earlier inspected reference in specification 0217-skill-security-extensibility-standard described Skill Fabric as abandoned with foundation code already shipped. Determine whether the remaining scope was discontinued or continued elsewhere. A documentation copy of this specification also exists and should not be counted as an independent outcome. 
- Agreement or disagreement with inherited decision: The source’s abandoned status is directly supported by the document. Its suitability as an abandonment training label remains unresolved. 
- Remaining evidence needed: Inspect the commit introducing status: abandoned, any accompanying explanation, and specification 0217-skill-security-extensibility-standard to establish timing, delivered scope, and possible supersession.


### Specification 0217 confirms that some Skill Fabric work carried forward.
### The document explicitly:
- Describes 0205 as abandoned with foundation code already shipped.
- Says its security work builds on 0205’s scanner and registry schema.
- Defers full website and CLI implementation to later work.

**This supports partial delivery and continuation of related scope. It does not prove that every remaining requirement from 0205 was replaced or completed. I inspected documentation, not the referenced implementation.**

### Updated fields:
- Evidence actually inspected (URL/revision and relevant passage or code): .specweave/increments/_archive/0205-skill-fabric/spec.md and .specweave/increments/_archive/0217-skill-security-extensibility-standard/spec.md, revision 882faa614f2bc7b3c1ec137f21f41be4a843edf2. Specification 0205 records status: abandoned. Specification 0217’s Dependencies section reports that 0205’s foundation code had shipped. Its FR-001 explicitly builds on the security scanner and registry schema from 0205; FR-002 and Out of Scope defer full website and CLI implementation.
- Your scope status and reasoning: Source-declared abandoned; final research classification remains unresolved. Documentation reports partial delivery and continued use of the security and registry foundation. This does not establish that the entire original scope was discontinued without a successor.
- Supported event date and precision, or unknown: Unknown. Neither the inspected dependency statement nor 0205’s status establishes the abandonment date. Specification 0217’s creation date is not an abandonment event date.
- Rename, replacement, scope change, or shared-outcome concerns: Explicit continuation of part of 0205’s foundation under 0217. The original documentation, CLI discovery, and contributor requirements need separate mapping before deciding whether the remaining scope was abandoned or superseded.
- Agreement or disagreement with inherited decision: Retain the source’s abandoned status as recorded, but do not yet convert it into a confirmed binary abandonment label.
- Remaining evidence needed: Inspect the commit introducing 0205’s abandoned status and its rationale. Determine which original requirements shipped, continued elsewhere, or were explicitly discontinued.


### I found metadata.json in the previous path, which provides:
- Foundation code had shipped.
- The branding shifted toward verified-skill.com under specification 0217.
- Related content was superseded by work in 0217.
- The README natural-language rewrite remained a separate unfinished task.
- The recorded abandonment timestamp is February 15, 2026, at 19:07:44.627 UTC.


**The earlier file history begins with an umbrella-repository import on February 17. Therefore, the timestamp is a source-recorded event date, not a status transition I independently observed in this repository’s commits.**

### Updated fields:
- Evidence actually inspected (URL/revision and relevant passage or code): Commit 40568b3a860fd32e9697adef3f54e2efb5303806 moves Skill Fabric files into _archive without content changes. At parent revision 5d54d6ddaecaa7d0ac8fc408a1648392384ad906, .specweave/increments/0205-skill-fabric/metadata.json contains abandonedReason and abandonedAt. The explanation reports shipped foundation code, a product-direction change toward specification 0217, superseded content, and one remaining README task.
- Your scope status and reasoning: Superseded/re-scoped after partial delivery. Preserve the source status as abandoned, but the recorded rationale supports substantial continuation under 0217 rather than discontinuation of the whole scope without a successor.
- Supported event date and precision, or unknown: February 15, 2026, at 19:07:44.627 UTC, as recorded in abandonedAt. Timestamp precision is milliseconds; the actual status transition was not independently verified through commit history.
- Rename, replacement, scope change, or shared-outcome concerns: Explicit product-direction change and continuation under 0217. The February 22 commit is an archive move. Earlier history begins with an import, limiting reconstruction of the original timeline.
- Agreement or disagreement with inherited decision: Retain abandoned as the source’s administrative status. Interpret the research outcome as superseded/re-scoped under the proposed definition.
- Remaining evidence needed: Original pre-import history would be needed to reconstruct baseline eligibility and independently verify the event timing. The remaining README task should not be treated as abandonment of the entire specification.



## Candidate A03: Sync Pipeline E2E Test

- Repository: anton-abyzov/specweave-umb
- Record ID: a75009a6290ccd86
- Specification: 0481-sync-pipeline-e2e-test


- Reviewer and review date: Jeremiah Briggs 10/26/26
- Concrete scope being evaluated: Verification that the existing synchronization pipeline creates documentation and synchronizes an increment to GitHub Issues, JIRA, and Azure DevOps.
- Evidence actually inspected (URL/revision and relevant passage or code): .specweave/increments/_abandoned/0481-sync-pipeline-e2e-test/spec.md, revision 882faa614f2bc7b3c1ec137f21f41be4a843edf2. The frontmatter records type: experiment and status: abandoned. The Overview describes integration verification, and Out of Scope explicitly excludes code changes. Four acceptance criteria are unchecked.
- Your scope status and reasoning: Source-declared abandoned; research eligibility and final label pending. The document records abandonment of a verification experiment, but provides no explanation or dated abandonment event.
- Supported event date and precision, or unknown: Unknown. March 10, 2026 is the recorded creation date, not an abandonment date.
- Evidence of unfinished, ongoing work at a prediction date, or unknown: Unknown. The snapshot does not establish status at a prediction date.
- Observed follow-up end and evidence coverage, or unknown: Unknown. This review covers the specification snapshot, not complete execution records or subsequent history.
- Rename, replacement, scope change, or shared-outcome concerns: The work is a verification experiment rather than feature implementation. Determine its eligibility using a consistent study-wide rule. Replacement or continuation has not been assessed.
- Agreement or disagreement with inherited decision: The source explicitly records abandonment. There is insufficient evidence to establish its timing or suitability as a training label.
- Remaining evidence needed: Establish whether verification experiments belong in the study population. If included, inspect the status-changing commit and execution records for the reason and timing of discontinuation.

### I found metadata.json in the previous path, which provides:
- It is marked abandoned.
- abandonedReason says “No reason provided.”
- abandonedAt records March 11, 2026, at 06:30:39.613 UTC.
- It was created less than a day earlier.

### Updated fields:
- Evidence actually inspected (URL/revision and relevant passage or code): .specweave/increments/_abandoned/0481-sync-pipeline-e2e-test/spec.md and metadata.json, revision 882faa614f2bc7b3c1ec137f21f41be4a843edf2. The specification describes a verification experiment. Metadata records status: abandoned, abandonedReason: No reason provided, and abandonedAt: 2026-03-11T06:30:39.613Z.
- Your scope status and reasoning: Source-declared abandoned experiment. The administrative status and timestamp are documented, but the reason for discontinuation and possible replacement remain unknown.
- Supported event date and precision, or unknown: March 11, 2026, at 06:30:39.613 UTC, as recorded in metadata. Not independently verified against the status-changing commit.
- Remaining evidence needed: A cancellation explanation or status-changing commit would be needed to establish the circumstances. Study-wide eligibility for verification experiments remains unresolved.

### **Screening decision**:
Under the proposed seven-day observation window, this case would be excluded: its recorded abandonment occurred before that prediction point. That exclusion does not depend on resolving whether experiments belong in the study.



## Candidate A04: Hook Execution Visibility and Command Reliability

- Repository: anton-abyzov/specweave-umb
- Specification: 0161-hook-execution-visibility-and-command-reliability


- Reviewer and review date: Jeremiah Briggs 10/26/26
- Concrete scope being evaluated: Hook failure warnings, logging, diagnostic commands, session cleanup, command routing, and reflection restoration.
- Evidence actually inspected (URL/revision and relevant passage or code): .specweave/increments/_archive/0161-hook-execution-visibility-and-command-reliability/spec.md, metadata.json, and tasks.md, revision 882faa614f2bc7b3c1ec137f21f41be4a843edf2. Metadata records abandonment after the core issue was reportedly fixed through metadata repair. Tasks T-001–T-007 are marked completed; T-008–T-018 remain pending. Specification history begins at import commit 38db8e72d8c516e9171194bd32ed755af1f5224a, dated February 17, 2026.
- Your scope status and reasoning: Documented discontinuation after reported partial completion and an alternative resolution of the core problem. Retain the source status as abandoned; classification under the stricter research definition remains unresolved.
- Supported event date and precision, or unknown: January 20, 2026, at 05:27:11.616 UTC, recorded in abandonedAt. Not independently verified against a status-changing commit.
- Evidence of unfinished, ongoing work at a prediction date, or unknown: Unknown. Metadata reports an earlier start, but the inspected repository history does not establish what was observable at a pre-event prediction date.
- Observed follow-up end and evidence coverage, or unknown: Pre-event coverage is unavailable in the inspected history. The first observed specification commit is after the recorded abandonment.
- Rename, replacement, scope change, or shared-outcome concerns: The stated core problem was resolved differently, and remaining work was deemed redundant or misdirected. Imported history prevents reconstruction of the original development sequence.
- Agreement or disagreement with inherited decision: Agree that the source explicitly records discontinuation. Do not treat it as a verified positive training label under the current protocol.
- Remaining evidence needed: Original pre-import history and supporting repair evidence would be required to reassess temporal eligibility and outcome classification.

### Screening decision:
Exclude from the current predictive cohort because pre-event history is unavailable.



## Case 21: abapify/adt-cli

- Identifier: `5085b857e44aa103`
- Stratum: Unclear
- Specification path: `openspec/changes/add-aclass-parser/specs/aclass/spec.md`
- Review group: `180d2e5bf1bdf9b79726`
- [Local packet](review_packets/5085b857e44aa103.md)
- [Specification snapshot](https://github.com/abapify/adt-cli/blob/a52b9a89c756bb496818246762b97500cce983ec/openspec/changes/add-aclass-parser/specs/aclass/spec.md)
- [Inherited evidence link](https://github.com/abapify/adt-cli/pull/111 | https://github.com/abapify/adt-cli/blob/a52b9a89c756bb496818246762b97500cce983ec/packages/aclass/tests/roundtrip.test.ts | https://github.com/abapify/adt-cli/blob/a52b9a89c756bb496818246762b97500cce983ec/packages/aclass/src/parser.ts)
- Inherited status: unclear


Substantial structural parser and fixture coverage are implemented in PR111. The selected spec explicitly makes parse-to-abapAstPrint roundtrip equality a release gate; the pinned roundtrip.test.ts instead checks declaration counts, repeated-parse shape and preserved body slices, without invoking a printer. Parser comments also document a statement-based alternative to CstParser. Strict recorded-scope completion is unconfirmed; no abandonment inferred.

**Your review:**

- Reviewer and review date: Jeremiah Briggs 10/26/26
- Concrete scope being evaluated:ABAP structural parser, including the required parse-and-print round-trip validation.
- Evidence actually inspected (URL/revision and relevant passage or code):packages/aclass/tests/roundtrip.test.ts, revision a52b9a89c756bb496818246762b97500cce983ec. The tests check structural properties, repeated parsing, and preserved method bodies. This file does not invoke a printer or compare regenerated source with the original.
- Your scope status and reasoning:Unclear. The inspected tests do not demonstrate the specification’s required round-trip comparison. This finding does not establish abandonment or prove that the functionality is absent elsewhere.
- Supported event date and precision, or unknown:Unknown. No completion or abandonment event date established.
- Evidence of unfinished, ongoing work at a prediction date, or unknown:Unknown. Historical status at a prediction date has not been established.
- Observed follow-up end and evidence coverage, or unknown:Unknown. Complete follow-up coverage has not been assessed.
- Rename, replacement, scope change, or shared-outcome concerns:Not assessed. Check whether the round-trip requirement was explicitly revised, deferred, or replaced.
- Agreement or disagreement with inherited decision:Provisionally agree with the inherited unclear decision because the inspected test file does not demonstrate the required round-trip validation.
- Remaining evidence needed:Check whether another test implements the required comparison or whether an explicit scope change removed that requirement.



## Case 22: archmaxai/archmax

- Identifier: `628ce9bb941e1d47`
- Stratum: Unclear
- Specification path: `openspec/changes/add-dataset-detail-panel/specs/semantic-models/spec.md`
- Review group: `b654006bd7a4896d3a2c`
- [Local packet](review_packets/628ce9bb941e1d47.md)
- [Specification snapshot](https://github.com/archmaxai/archmax/blob/3aa7c1208a8ea686d08703f14e4ccc1066f0eecd/openspec/changes/add-dataset-detail-panel/specs/semantic-models/spec.md)
- [Inherited evidence link](https://github.com/archmaxai/archmax/commit/4ed03992f0b7269910b255e7068b2db5a5baf732 | https://github.com/archmaxai/archmax/commit/314a63595adc66eb3a891b0630db83370ddbc0fa | https://github.com/archmaxai/archmax/blob/3aa7c1208a8ea686d08703f14e4ccc1066f0eecd/apps/frontend/src/components/model-visualization/dataset-detail-panel.tsx)
- Inherited status: unclear


Dataset panel, typed metadata API, save handling and synonyms/examples editing are substantially implemented. The recorded spec additionally requires each field entry to show its ai_context. At pinned revision3aa7c12, the field renderer shows name/type/description only and does not render field.ai_context. Strict completion is therefore unclear; no abandonment is inferred.

**Your review:**

- Reviewer and review date: Jeremiah Briggs 10/26/26
- Concrete scope being evaluated: Dataset detail panel, particularly the requirement to display each field’s name, data type, description, and AI context.
- Evidence actually inspected (URL/revision and relevant passage or code): apps/frontend/src/components/model-visualization/dataset-detail-panel.tsx, revision 3aa7c1208a8ea686d08703f14e4ccc1066f0eecd. The dataset.fields.map rendering section displays field names, data types, and editable descriptions, but does not render field-level ai_context.
- Your scope status and reasoning: Unclear for full completion. The inspected component implements substantial panel functionality but omits the specified field-level AI context display. No evidence of abandonment was established.
- Supported event date and precision, or unknown: Unknown. No full-completion or abandonment event date established.
- Evidence of unfinished, ongoing work at a prediction date, or unknown: Unknown. Status at a prediction date has not been reconstructed.
- Observed follow-up end and evidence coverage, or unknown: Unknown. Review covers the recorded component snapshot, not complete subsequent history.
- Rename, replacement, scope change, or shared-outcome concerns: Not established. Check whether field-level AI context display was explicitly removed from scope, deferred, or implemented elsewhere.
- Agreement or disagreement with inherited decision: Provisionally agree with unclear; the inspected component supports the reported field-level display gap.
- Remaining evidence needed: Inspect related changes and discussion for a revised requirement or later implementation of field-level AI context. Confirm relevant behavior through tests or application execution where feasible.


## Case 23: zhuanggenhua/BoardGame

- Identifier: `734a4c4bfbcd9eab`
- Stratum: Unclear
- Specification path: `openspec/changes/add-seat-emotes/specs/match-emotes/spec.md`
- Review group: `6318bd6a9fc204ebdcb1`
- [Local packet](review_packets/734a4c4bfbcd9eab.md)
- [Specification snapshot](https://github.com/zhuanggenhua/BoardGame/blob/d6518bc5506eff138cdf4540d89ad52802d88b33/openspec/changes/add-seat-emotes/specs/match-emotes/spec.md)
- [Inherited evidence link](https://github.com/zhuanggenhua/BoardGame/commit/fd5026b82958bbfa8278db37cf441ec3824a824a.patch | https://github.com/zhuanggenhua/BoardGame/commit/14701860aa666a3c099d707e1bc713258ed45f0b.patch | https://raw.githubusercontent.com/zhuanggenhua/BoardGame/da82e67afbbe9af038e4897666f2cd564126ae99/server.ts | https://raw.githubusercontent.com/zhuanggenhua/BoardGame/d6518bc5506eff138cdf4540d89ad52802d88b33/server.ts)
- Inherited status: unclear


Shared catalog, transient broadcast, cooldown, seat-anchor display and sender-echo behavior have substantive implementation/test evidence. The explicit server membership/spectator rule is unresolved: identical pinned handlers accept caller-supplied playerId and validate occupied seat metadata, without a traced caller-to-seat credential check. No exploit or live server test was performed.

**Your review:**

- Reviewer and review date:Jeremiah Briggs 10/26/26
- Concrete scope being evaluated: In-game seat emotes, particularly server-side validation of match membership and rejection of spectator requests.
- Evidence actually inspected (URL/revision and relevant passage or code): server.ts and src/server/matchEmotes.ts, revision d6518bc5506eff138cdf4540d89ad52802d88b33. The join/send handlers accept player identifiers and call validation helpers. resolveMatchEmoteJoinDecision checks seat metadata, but the inspected functions do not verify the caller’s ownership of that seat.
- Your scope status and reasoning: Unclear for full completion. Emote handling and validation logic exist, but the required spectator restriction has not been fully verified. No abandonment established.
- Supported event date and precision, or unknown: Unknown. No full-completion or abandonment event date established.
- Evidence of unfinished, ongoing work at a prediction date, or unknown: Unknown. Historical status at a prediction date has not been reconstructed.
- Observed follow-up end and evidence coverage, or unknown: Unknown. Review covers selected source code at the recorded revision, not complete follow-up history.
- Rename, replacement, scope change, or shared-outcome concerns: Not assessed. Authentication elsewhere in the application may affect this finding.
- Agreement or disagreement with inherited decision: Provisionally agree with unclear; the caller-to-seat validation remains unresolved in the inspected code.
- Remaining evidence needed: Trace socket authentication and credential validation to determine whether the caller is bound to the claimed seat. Inspect relevant tests for spectator rejection. Verify behavior in a local test environment if needed.

