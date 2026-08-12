# AI Knowledge Agent - Mandatory Project Execution Rules

These rules apply to the AI Knowledge Agent POC project (repo: AI-Knowledge-Agent).
You must obey these rules for EVERY phase from Phase 1 through Phase 14.

## BEFORE STARTING ANY PHASE
- Read `docs/PROJECT_HANDOFF.md`.
- Read `.agents/AGENTS.md`.
- Read `README.md`.
- Determine the current completed phase and the exact next phase based on the repository state.
- **Never rely** on Antigravity chat history, brain/context files, task logs, or previous IDE state to determine project status.
- Treat `docs/PROJECT_HANDOFF.md` as the authoritative project state.
- If there is any conflict between chat history and `docs/PROJECT_HANDOFF.md`, inspect the repository and resolve the discrepancy before proceeding. Do not blindly trust chat history.
- If the repository is cloned onto another laptop, you must be able to understand the entire project state solely from the repository source code, `docs/PROJECT_HANDOFF.md`, `.agents/AGENTS.md`, and `README.md`.

## MANDATORY PHASE COMPLETION PROTOCOL (AUTOMATIC)
At the end of EVERY phase, you MUST automatically and WITHOUT requiring the user to explicitly ask, perform the following sequence BEFORE declaring the phase complete or proceeding to another phase:
1. Verify the implementation is actually complete.
2. Run all relevant tests.
3. Run required Docker/EC2/SSM validation where applicable.
4. Verify the acceptance criteria.
5. Perform a security/secrets check (secret scan).
6. Inspect `git diff`.
7. Update `docs/PROJECT_HANDOFF.md` with the complete execution record.

The handoff MUST be updated with:
- Current project status
- Current architecture if changed
- Completed phase number
- Phase name
- Phase objective
- What was implemented
- Files changed
- Important technical decisions
- Tests performed
- Test results
- EC2/SSM validation results, if applicable
- Docker validation results, if applicable
- Acceptance criteria and whether they passed
- Important bugs/issues encountered and their fixes
- Relevant commit hash
- Current branch
- Current HEAD
- Repository synchronization status
- Security status
- Next phase number
- Next phase name
- Next phase status

The handoff update is mandatory and must happen automatically. You should NEVER have to be reminded to update `PROJECT_HANDOFF.md`.

## PHASE STATUS RULE
After completing Phase N:
- Phase N = COMPLETE
- Phase N+1 = NEXT / NOT STARTED
- All later phases = NOT STARTED
- Do not mark a future phase as complete unless it has actually been implemented and verified.
- Mark ONLY the completed phase as COMPLETE.

## GIT AND SECURITY RULE
Before committing, always run:
- `git status`
- `git diff`
- appropriate tests
- secret scan
- `git status` after commit/push

Never commit:
- `.env`
- API keys
- AWS credentials
- secrets
- temporary SSM command files
- `cmdId*.txt` or `cmdId` files
- `b64*.txt` or `b64` files
- temporary debugging scripts
- Antigravity brain/task artifacts
- generated local IDE artifacts

After updating `PROJECT_HANDOFF.md`:
- Review `git diff`.
- Ensure no secrets/`.env`/temporary files are present or tracked.
- Commit the implementation and handoff documentation together.
- Push to `origin/main`.
- Run `git status` and verify the working tree is clean.

## PRESERVATION RULE
Never modify or remove working project functionality merely to make the repository clean. Temporary artifacts may be removed only when they are confirmed not to be required by the application.

## IMPORTANT STOP RULE
After completing a phase:
1. Complete the handoff update (`PROJECT_HANDOFF.md`).
2. Commit the changes.
3. Push to `origin/main`.
4. Verify clean working tree.
5. Report the completed phase.
6. **STOP**.

Do NOT automatically start the next phase after completing the current phase. Wait for explicit instruction before starting the next phase.
