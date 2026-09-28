# Oasis Attend validation — 5 September 2026

Maintenance scope: product rename/settings migration, pyzatt connector replacement, product icons, folder-based packaging/replaceable python-bidi, updated notices/EULA, and cross-source punch deduplication. No UI framework change or restyling was undertaken.

Automated checks cover the original attendance/password/role behavior, legacy punch consolidation and repeated import with different state/source values, preservation of first-seen origin, duplicate archive/audit count, reopening without a second migration, atomic rollback on failure, and settings migration without overwriting newer settings.

Connector checks cover user/attendance field mapping, failure cleanup, explicit unsupported UDP/auth rejection before network access, fragmented TCP replies/EOF, a 2,000-record dataset larger than 65,535 bytes, and an end-to-end exchange with a simulated local TCP terminal using the actual pyzatt library. Synthetic records only.

Source and compiled portable smoke checks exercise both languages, admin/report-only navigation, product logo/icon resources, PDF/XLS/XLSX/HTML exports, and external `bidi` file loading. The release audit checks that pyzk/`zk` is absent and the `bidi` Python modules are outside PYZ. The Inno installer is built from this same folder layout with SetupIconFile and the supplied EULA.

Real MB20, MB1000, MB2000 and uFace800 devices have not been tested. This upstream pyzatt API is TCP-only and lacks communication-password support, so UDP and keyed-device testing cannot pass with this connector. Device firmware compatibility remains open. Physical printing and installation on a separate PC remain untested. The installer compilation is not an end-to-end customer-installation test.

The product-mark and wordmark addition preserves the existing Tkinter framework. The UI prompt's full restyling/RTL/theme/accessibility acceptance checklist remains deferred pending the user's framework decision.
