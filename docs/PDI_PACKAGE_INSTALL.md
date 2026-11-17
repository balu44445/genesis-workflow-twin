# GENESIS installation package

**Version boundary:** This guide describes the earlier `GENESIS-PDI-Demo.zip` and its sequential gateway. The new `GENESIS-Workspace-0.2.zip` is a separate source/wheel package and does not contain an updated live-tested XML transport. Follow CONCURRENCY_UPGRADE.md before installing its changed gateway.

The private package contains a curated XML transport downloaded from the completed GENESIS update set on the validation PDI, the reviewed JavaScript sources, example manifests, this installation guide, a repeatable demo runbook, and the live validation report. The XML transport is intentionally excluded from this public repository. Import into another instance has **not** been performed.

## Export review

The original downloaded update set contained 43 customer updates, including unrelated platform updates. The delivery XML retains only the 37 GENESIS configuration updates. Six unrelated records were excluded: an ECC queue policy, a password-reset process, two platform properties, and two crypto module key policies. The original export remains private and is not included in the package. See EXPORT_AUDIT.json and SHA256SUMS.txt for inventory and integrity checks.

The curated transport retains genuine exported record IDs and payloads. Its XML was parsed and its five scripts checked against the supplied source. This verifies package contents; it does not establish import compatibility.

## Install on a development instance

1. Back up any existing GENESIS configuration. Use a dedicated development update set and record the target release/build. The source instance is Brazil, build `glide-brazil-08-25-2026__patch2-10-22-2026`.
2. As admin, import the curated XML through **Retrieved Update Sets → Import Update Set from XML**. Preview it, inspect every collision/dependency, and resolve issues before committing. The package does not automatically commit changes.
3. Verify all table fields, Script Includes, API resources, role, ACLs, and role links against PDI_SETUP.md. Use temporary security_admin elevation only where the platform requires it, then remove it.
4. Synthetic users, user-role assignments, and request data are **not transported** by this update set. Create new active Alice/Bob/Carol accounts and explicitly assign the demo role; add Explorer access only for the interactive demo. Do not assign admin or reuse source-instance user IDs.
5. The exported manifest contains source-instance actor IDs. Replace all three IDs with actual target sys_user IDs before testing. Keep revision `demo-fixed-1`, the correct eligibility lists, and `require_distinct_approver=true`. Keep property read/write access admin-only. The supplied example manifests are templates and also require ID mapping.
6. Read the actual GENESIS Base API path from the target instance; do not assume `/api/global/genesis` or copy the source namespace blindly. Check the endpoint ACL association and authentication/authorization on every resource.
7. Test model export, all three scenarios, anonymous and missing-role denials, direct table write denial, and post-denial persisted state. Use PDI_DEMO_RUNBOOK.md. Record target results separately; source PDI tests do not certify the target.

For private external extraction, use instance-supported OAuth or a dedicated account via secure authentication over verified HTTPS. Never put secrets in URLs, scripts, source control, or evidence. No OAuth client/token or password is provisioned by this package.

## Recovery and limits

Preserve an installation inventory and target backup before import. Review the platform's available backout behavior in the target instance; do not assume user/data changes are undone by update-set backout. No automatic cleanup or deletion is included.

The live report describes the tested source instance. The model proof is bounded to depth 3, and runtime behavior is sequential. This package is a synthetic demonstration, without atomic concurrency protection, real provisioning, or arbitrary Flow Designer/ACL extraction.
