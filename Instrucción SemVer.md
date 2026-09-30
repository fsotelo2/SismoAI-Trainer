# Permanent Instruction: Mandatory Semantic Versioning (SemVer)

**Type:** Development rule
**Applies to:** All project code, firmware, modules, tools, and deliverables
**Requirement:** Always

## 1. Objective

As a coding agent, apply and consistently follow Semantic Versioning (SemVer) throughout the project. The version number must communicate the scope and compatibility of each change.

Do not invent, omit, reset, or alter the version structure. Before modifying files, identify the current version and determine which increment applies.

## 2. Required format

The version must use exactly this structure:

`MAJOR.MINOR.PATCH`

Example: `1.4.2`

- **MAJOR:** incompatible changes with previous versions.
- **MINOR:** new features that are compatible with previous versions.
- **PATCH:** compatible fixes that do not add functionality with its own scope.

All three components are non-negative integers separated by periods. Do not use formats such as `1.4`, `v1.4.2.7`, `1.4.2.0`, or extra text within the stable version number.

The `v` prefix may be used in Git tags (for example, `v1.4.2`), but it is not part of the SemVer version number.

## 3. Version increment rules

Apply these rules in order:

### 3.1 MAJOR

Increment MAJOR when a change breaks compatibility, for example:

- Changing or removing public interfaces, functions, commands, protocols, or structures such that existing consumers must be modified.
- Changing configuration or storage formats without preserving compatibility or providing migration.
- Changing module contracts in a way that requires other components to be adapted.

When incrementing MAJOR:

- Add 1 to MAJOR.
- Reset MINOR to 0.
- Reset PATCH to 0.

Example: `1.7.5` → `2.0.0`.

### 3.2 MINOR

Increment MINOR when adding a new, compatible capability, for example:

- Adding a module, function, endpoint, command, or optional parameter.
- Adding a screen, report, or export method without breaking existing behavior.
- Extending functionality while preserving existing contracts.

When incrementing MINOR:

- Keep MAJOR unchanged.
- Add 1 to MINOR.
- Reset PATCH to 0.

Example: `1.7.5` → `1.8.0`.

### 3.3 PATCH

Increment PATCH when fixing or adjusting software without incompatibly changing its interfaces or introducing a new feature with its own scope, for example:

- Fixing logic, validation, calculation, or exception-handling defects.
- Fixing visual or logging defects.
- Improving internal robustness without changing expected contractual behavior.

When incrementing PATCH:

- Keep MAJOR and MINOR unchanged.
- Add 1 to PATCH.

Example: `1.7.5` → `1.7.6`.

## 4. Precedence and special cases

1. If a change contains multiple change types, apply the highest-impact increment: **MAJOR takes precedence over MINOR, and MINOR over PATCH**.
2. Do not increment the version for every edited file. Classify the logical set of changes that will be delivered as one version.
3. If there are no software changes, do not increment the version.
4. If compatibility is uncertain, inspect consumers, tests, interfaces, and documentation. If doubt remains, do not claim compatibility: explain the uncertainty and ask for clarification before publishing.
5. Do not change the version to `1.0.0` merely because the code compiles. `1.0.0` declares a stable interface and compatibility contract.
6. In the `0.y.z` series, the project is in early development and compatibility is not guaranteed. Still use all three components and increment coherently. When reaching `1.0.0`, explicitly establish the stable baseline.

## 5. Pre-release versions

Use pre-release labels only if the project has an explicit pre-release process. Valid formats include:

- `1.3.0-alpha.1`
- `1.3.0-beta.2`
- `1.3.0-rc.1`

Do not use `alpha`, `beta`, or `rc` in place of MAJOR, MINOR, or PATCH. Do not add pre-release labels on your own if the project does not use them.

Build metadata, such as `1.3.0+build.45`, is optional and does not affect version precedence. Do not use it as the project's primary version number unless a convention is documented.

## 6. Single source of truth

Before changing the version, find the convention already established in the repository. Check, as applicable:

- `VERSION` or `version.txt`.
- `pyproject.toml`, `package.json`, configuration files, or manifests.
- Firmware or application version constants.
- Git tags and release notes.
- Documentation and release files.

If multiple copies of the version exist, identify the primary source and synchronize the others according to the project architecture. Do not leave conflicting versions.

If no version is defined:

1. Inspect the project's state and maturity.
2. Do not assume that a stable version already exists.
3. Propose a coherent initial version (normally `0.1.0` during development or `1.0.0` when an initial stable release is explicitly declared).
4. Report the decision and where it will be recorded.

Do not overwrite an existing version or reset numbering without explicit authorization.

## 7. Required procedure before coding

At the start of any task that modifies code:

1. Identify the current version and its source of truth.
2. Review repository status and prior user changes. Do not overwrite them or attribute them to your task.
3. Determine the request's scope and affected components.
4. Assess compatibility with existing interfaces, configuration, data, dependencies, and consumers.
5. Classify the change as MAJOR, MINOR, PATCH, or no increment.
6. Define the target version, but do not apply it until the complete change set actually matches that classification.

For analysis-only, explanation, review-without-edits, or diagnostic tasks, do not increment the version.

## 8. Required procedure before delivery

Before declaring a modification complete:

1. Verify that the target version follows `MAJOR.MINOR.PATCH` or an authorized pre-release format.
2. Confirm that the increment matches the actual impact of the change.
3. Update the source of truth and all required copies.
4. Check that no references to an older version remain in files that must reflect the current version.
5. Run the relevant tests and checks. Do not claim a test passed unless it was run.
6. Review the diff to confirm that no unrelated files were modified.
7. Record relevant changes in the version history if the project maintains one.

Do not mark a version as published or released if only local code was changed and the publication process was not completed.

## 9. Git and tags

When the project uses Git:

- Associate the version with the commit containing the corresponding delivery.
- Use annotated tags for published versions, with a `v` prefix if that is the repository convention.
- Do not create or move tags for published versions without authorization.
- Do not push, publish packages, or deploy without explicit authorization.
- Do not tag a version if required tests failed or if pending changes are not part of the delivery.

Example tag (only when authorized and appropriate):

```bash
git tag -a v1.4.2 -m "Release 1.4.2"
```

## 10. Version and change records

If the repository has a `CHANGELOG.md` or equivalent record, update it with relevant changes grouped by version. Use clear categories, for example:

- **Added:** new features.
- **Changed:** significant behavior or implementation changes.
- **Fixed:** fixes.
- **Removed:** removed capabilities.
- **Breaking Changes:** incompatible changes and required consumer adaptations.

Do not invent historical entries or attribute prior changes to the current task. If no changelog exists, do not create one unless it adds value to the project or is requested.

## 11. Dependencies and component versions

Distinguish the product version from dependency or module versions:

- Do not automatically increment the product version solely because a dependency was updated.
- Assess whether an update changes product behavior, compatibility, security, or requirements.
- If modules have independent versions, document their scheme and do not mix their numbers with the global version.
- In a monorepo with multiple packages, follow the existing strategy (joint or independent versioning).

## 12. Required user communication

For every delivery that modifies code, briefly report:

- **Previous version:** the version identified in the repository.
- **New version:** the applied version, or "no increment" if none applies.
- **Change type:** MAJOR, MINOR, PATCH, or none.
- **Justification:** why that increment applies.
- **Version files changed:** specific file list.
- **Checks:** tests run and their results; explicitly list tests not run.
- **Compatibility:** whether it is preserved, or what breaks and what adaptations are required.

Do not hide uncertainty, test failures, version inconsistencies, or breaking changes.

## 13. Prohibitions

The following are prohibited:

- Using a stable version structure other than `MAJOR.MINOR.PATCH`.
- Incrementing components arbitrarily or for cosmetic reasons.
- Resetting numbering without an explicit decision.
- Claiming compatibility without reviewing the impact.
- Changing the version merely to give the appearance of progress.
- Failing to update the source of truth.
- Leaving conflicting version numbers in files that must be synchronized.
- Creating tags, publishing, or deploying without authorization.
- Claiming versioning is correct without checking the relevant files.

## 14. Checklist

Before finishing, confirm:

- [ ] I identified the current version and its source of truth.
- [ ] I reviewed prior changes and preserved existing work.
- [ ] I classified the change according to compatibility and scope.
- [ ] I applied the correct increment, or justified why none applies.
- [ ] I kept exactly three numeric components in the stable version.
- [ ] I synchronized the required version files.
- [ ] I updated the changelog if applicable.
- [ ] I ran the relevant tests and reported their actual results.
- [ ] I did not publish or tag without authorization.
- [ ] I reported the previous version, new version, and justification.

## 15. Final instruction to the agent

These rules are mandatory throughout the life of the project. For every future task that modifies software, repeat the identification, classification, update, and verification procedure. If another instruction requests a format incompatible with SemVer, preserve SemVer and explain the conflict before making changes. Never sacrifice version traceability for speed.
