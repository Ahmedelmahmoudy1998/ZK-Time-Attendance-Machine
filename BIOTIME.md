# Import attendance from BioTime — Oasis Attend 1.1.9

Keep the terminal connected to the working BioTime ADMS server. In Oasis Attend, sign in as an administrator and choose **Devices → Import from BioTime**.

1. Enter the BioTime server URL. Use `http://127.0.0.1` when BioTime runs on this PC. For a different PC, use its HTTPS address with a valid trusted certificate. The port can be included in the URL.
2. Enter your **BioTime** username/password, which can differ from your Oasis Attend login. Your BioTime account must have API access to attendance transactions; availability can depend on BioTime permissions/license.
3. Copy the device's serial number from **BioTime → Device**. This is not the IP address or the device's communication key.
4. Choose dates and click **Read attendance**. Review the device, dates, employee count and punch count, then confirm the import.
5. Generate the Oasis Attend report for the same dates.

The server address, username and serial are remembered on this PC after a successful download. Passwords and API tokens are held only for the current download and are not saved. There is no automatic background synchronization: repeat Read attendance to retrieve new punches.

Before importing, Oasis Attend creates a complete backup of the selected database under `%LOCALAPPDATA%\Oasis Attend\backups`. The confirmation shows its path. Backups contain your attendance data and accounts; protect them like the original database.

The import adds employees referenced by the selected punches and their attendance. Existing employee names/departments and punches are preserved. It does not import employees with no punches in the selected period, alter BioTime, change device settings, send commands to the device, clear records, or access biometric templates. A punch is deduplicated by badge and time to the second, including punches previously imported directly or from MDB. Employee badge numbers must identify the same person across your sources.

Dates follow BioTime's documented device-local `punch_time`, without timezone conversion. Unexpected zoned or invalid dates are rejected. Up to 367 days can be requested at once. The entire download is validated before import; incomplete pagination, changing totals, mismatched devices, authentication errors, and invalid records abort without importing a partial batch. If attendance arrives during a download and the total changes, retry or select a completed period.

Implementation uses the documented `/jwt-api-token-auth/` authentication endpoint and GET `/iclock/api/transactions/`, including `terminal_sn`, `start_time`, `end_time`, `page` and `page_size`. Pagination remains on the same server and endpoint; redirects are rejected. HTTPS certificate checks remain enabled. No direct access to BioTime's database or browser session is used.

Validation: tested against a local simulated BioTime API, including pagination, login rejection, duplicate import, backup, rollback, device/date filtering and unsafe redirects. Real BioTime account access must be verified by signing in through the new import form. The MB20-VL's direct port-4370 error 6001 remains unresolved; this integration uses the working BioTime route instead.
