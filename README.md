# Oasis Attend

Owner: **Oasis Digital Solutions**. Arabic product name: **حضور أوايسس**. Brand accent: **#D39340**. This maintenance release retains Tkinter; the UI framework decision and restyling are deferred.

## Run or install

Version 1.1.12 fixes ADMS timestamps to match the existing importer exactly, preventing duplicate punches across direct and BioTime imports. Regression tests exercise both import paths and report generation.

Version 1.1.11 adds **Devices → Receive from device (ADMS)** for standalone attendance reception, with no BioTime dependency. Configure the terminal to send to the PC on port 8081, start the receiver, and keep Oasis open and logged in. Batches commit before acknowledgement; replays are deduplicated. Includes saved settings, automatic backup, live contact/upload status, and a read-only historical attendance request. See [ADMS.md](ADMS.md). Reply 6001 now offers this receiver. Live ADMS contact and historical attendance transfer have been verified with an MB20-VL; other models still need testing.

Version 1.1.10 replaces the unhelpful direct-connection error 6001 with an option to open **Import from BioTime** immediately. The direct connection remains unsupported for affected devices; the prompt offers the existing BioTime importer and does not claim a successful download.

Version 1.1.9 adds **Devices → Import from BioTime**. It reads attendance through BioTime's documented API, with a device serial number and date range, a preview, and an automatic Oasis database backup before import. Repeated imports skip existing punches and preserve existing employee details. See [BIOTIME.md](BIOTIME.md) for setup and limitations. This does not change the direct TCP connector or fix device reply 6001; BioTime must remain running and receiving the terminal's ADMS data.

Version 1.1.8 combines each date display and calendar opener into one gold date control. Click the date or use Enter, Space or Down to choose a date. Print preview and the calendar's Today action use the same accent as Generate in both themes.

Version 1.1.7 adds coordinated **Light / Dark** appearance options on the login screen, in the app header, and under Settings. Light mode uses white panels with navy and gold accents; dark mode uses charcoal panels with gold accents. The choice is saved on this PC and applies immediately without losing open forms or selected filters. Tables, calendars and dropdowns follow the chosen appearance; exported reports retain their print-friendly colors.

Extract the portable folder and run `portable/Oasis Attend/Oasis Attend.exe`. Keep `_internal` and the license/source notices alongside the executable. Python is included. Windows 10/11 x64 is the target. Alternatively, use `installer/Oasis Attend Setup.exe`; the installer places the same folder layout under the current Windows user's Programs directory and creates shortcuts. Binaries are unsigned.

First run automatically copies `%LOCALAPPDATA%\ZKDesk\settings.json` to `%LOCALAPPDATA%\Oasis Attend\settings.json` when the new file does not exist. The old settings and chosen database remain in place. An existing new settings file always wins. Your database selection, language and accounts are retained. If a saved database is unavailable, its path is kept and a recovery screen is shown. A new installation asks for a `.sqlite` database and an administrator password of at least eight characters (no required uppercase letters, numbers, or symbols).

## Devices and MDB import

Version 1.1.6 fixes U160-C downloads that failed on Arabic names. The name reader stops at the end marker and retains complete characters when the terminal truncates a name at its 24-byte limit. Malformed display-name bytes no longer stop attendance downloads; badge numbers and record lengths remain strictly validated. The adapter does not change names or records on the device.

Version 1.1.5 saves each device's **Communication key (0 if none)** directly after its IP address in **Devices → Add / Edit**, and displays it beside the IP in the device list. Downloads use the saved value without prompting each time. Existing devices start at 0; set another value only if configured on the terminal. Zero-key authentication challenges are now supported, and rejected keys still fail normally.

The connector uses MIT-licensed pyzatt 2.0.0 pinned to upstream commit `dc30714ed641388f53537319f6c0e7bd8dba544a`. No pyzk library or archive ships in this release. The adapter reads users and attendance logs, with a 20-second socket timeout, complete TCP frame reads, socket cleanup and full 32-bit dataset lengths.

**The connector supports TCP only.** The app adds communication-key authentication to pyzatt, including terminals that require authentication with key 0. UDP remains unsupported. Existing device settings are preserved. A live device download with key 0 has been verified; model-specific compatibility across MB20, MB1000, MB2000 and uFace800 has not been established for every model.

MDB import reads a temporary copy through Microsoft ACE 64-bit OLE DB. Employees, attendance and machine settings are imported; legacy schedules are not. The original MDB is not edited. No production database is included in this package. Employee changes remain local and are not pushed to machines. No biometric templates are downloaded and no device logs are cleared.

## Punch deduplication upgrade

Version 1.1.4 fixes ZK attendance dates decoded with the wrong year. The device format uses twelve 31-day slots per year; treating it as 365 days could place 2026 punches in 2027. Install the update and download users and logs again, then regenerate the report. Matching old imports from the same device are corrected only when re-reading their original records, with the previous timestamps retained in `punch_time_repair_archive` and an audit entry. Records from other sources and timestamps also present as real device records are left unchanged. Back up the database before upgrading.

One physical punch is identified by **badge and timestamp to the second**, regardless of its source or punch-state encoding. On first opening an older database, an atomic migration keeps the earliest stored row for that identity, including its first-seen `kind` and `source`. Removed duplicates are preserved in `punch_duplicate_archive`; an audit entry records the number consolidated. Reopening does not repeat the migration. Re-importing the same MDB/device punch no longer inflates the Attendance list or dashboard. Two genuinely different events for the same employee at exactly the same second are represented as one punch, consistent with existing report calculations.

## Roles, shifts and reports

- `reports`: dashboard and reports/export.
- `manager`: reports, local employee edits, attendance view, shifts and assignments.
- `admin`: devices, downloads, imports, accounts, audit, backups and settings as well.

Passwords use salted PBKDF2-SHA256, 600,000 iterations; five failed attempts lock an account for five minutes. Protect database files using Windows permissions: application roles do not encrypt SQLite or prevent direct file access. Account passwords can be reset by an administrator.

Employee dropdowns show badge and name. Shifts have start/end, grace, unpaid break, weekdays and dated assignments. Equal start/end and overlapping dated assignments are not supported. Weekdays use Monday=0 to Sunday=6. End before start means overnight.

Reports are first/last punch spans minus the fixed break, not IN/OUT pair totals. Single punches are flagged and counted as zero worked minutes; completed scheduled days without punches are absent. Future/current shifts are pending/in progress. Review rotating schedules, long overtime and missed scans before payroll use. Holidays, leave, manual corrections, payroll rules and shift-pair policy are outside this release.

Daily, calendar-month and inclusive custom-period reports export CSV, PDF, XLS, XLSX and browser print preview. Preview opens locally; the user chooses printing. XLS preserves badge text/leading zeros and splits large outputs across sheets. Arabic PDF output uses Windows Arial and python-bidi. Detailed PDFs use landscape A3; shorter summaries use A4. Raw attendance shows the latest 10,000 matching records; audit shows 1,000. Reports cover up to 367 days.

Use a local SQLite file. Simultaneous multi-PC operation needs a server database/API; sharing this file over a network is not the supported architecture. Back up before upgrades. Backup databases include accounts and can be selected at login for restoration.

## Branding and license

Version 1.1.2 adds **Settings → Company details** for administrators to change the company name, branch and logo. These are saved inside each attendance database and appear in PDF, Excel and print-preview reports. CSV includes the company and branch as text. See [COMPANY-SETTINGS.md](COMPANY-SETTINGS.md) for details.

The application is distributed under the supplied **proprietary Oasis Digital Solutions EULA**, in LICENSE.txt. Third-party components retain their own licenses and rights in THIRD-PARTY-NOTICES.txt. This replaces the old GPL product declaration only for this new release. The supplied EULA's template-review wording is retained; its not-yet-in-force block is removed as requested.

python-bidi remains an externally replaceable LGPL component; see REPLACING-BIDI.md and its included source. The app icon is `source/brand/app-icon.ico`; the 128px product logo appears above the existing ODS company wordmark on login. The window, executable and Inno Setup installer use the product icon.

## Build and test

Use 64-bit Python 3.12, run `source/build.ps1`, and install Inno Setup 6 to compile `source/installer.iss`. Requirements pin pyzatt to its upstream source commit because it is not published under that name on PyPI. The build excludes `zk`, uses `--onedir`, applies the external-bidi hook and regenerates notices. Tests cover migration/re-import/rollback, settings precedence, connector mapping and cleanup, unsupported transport rejection, fragmented frames and a 2,000-record synthetic dataset, plus the original attendance/authentication tests.

`Oasis Attend.exe --self-test C:\path\to\empty-test-folder` checks bilingual screens, branding, dependencies and all exports using synthetic data only. See VALIDATION.md for actual results and outstanding hardware checks.
