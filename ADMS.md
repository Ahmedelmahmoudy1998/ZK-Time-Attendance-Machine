# Direct attendance reception — Oasis Attend 1.1.11

Oasis Attend includes an ADMS HTTP receiver. Compatible terminals send attendance
directly into the selected Oasis SQLite database; BioTime is not required or contacted.
This is separate from the older **Download users + logs** TCP/4370 connection.

## Set up

1. Log into Oasis as an administrator. Open **Devices → Receive from device (ADMS)**.
2. Select this PC's LAN IPv4 address, receiver port **8081**, the device's IP address,
   and the serial number printed on the device or shown on its information screen.
3. Click **Start receiver**. Oasis backs up the selected database first and saves
   these settings for that database. Permit incoming TCP 8081 in Windows Firewall
   only from the device's IP address. Keep the PC address stable.
4. On the terminal, set **Cloud Server → ADMS**, domain name off, server address to
   the PC's LAN address, server port **8081**, proxy off, and HTTPS off.
5. Check **Last contact** and **Last saved upload**. Make a test punch and check
   **Received punches**. Refresh Attendance or regenerate Reports for that date.

Keep Oasis open and logged in. Closing the receiver settings window leaves reception
running. Logout, database change or exiting Oasis stops it. Start the receiver again
after reopening the app. Only one terminal is configured per running app instance.
The receiver does not need BioTime services, a BioTime account, or Internet access.

The terminal has one active ADMS destination: pointing it at Oasis stops new uploads
to its former BioTime destination. Previously saved data remains in both products.
The device communication key for TCP/4370 is not the ADMS receiver setting.

## Older attendance and names

The first handshake requests available attendance and user changes. For older
attendance, select a period and click **Request older attendance**. This sends only
the documented read command `DATA QUERY ATTLOG`; firmware support varies. A command
acknowledgement is not proof that all rows arrived. Compare attendance totals and
dates against the device. Pending requests can be cancelled; uploads already in
progress may still arrive. No delete, reset, enrollment or clock-setting commands
are issued.

Existing employee details are preserved. New badges without names initially use
the badge as their name; a later user upload fills that placeholder. You may also
edit employee names in Oasis. Biometric templates, images, user passwords and raw
request bodies are not retained.

## Reliability and limits

- Each validated batch, its audit entry and upload checkpoint commit together before
  success is sent. Malformed batches or unavailable/locked databases return an error
  so the device can retry. Do not clear records on the terminal before verifying them.
- Punch identity remains badge + timestamp to the second. Replays, including punches
  previously imported from BioTime, do not duplicate or overwrite attendance.
- Device timestamps are preserved as local wall-clock times. Verify the terminal's
  date and the report range. Standard ADMS responses advertise the PC time zone and
  current UTC time; firmware can use these for clock synchronization. Keep the PC's
  clock and time zone correct. No separate clock-setting command is sent.
- This is plain HTTP for a trusted LAN, restricted by device IP and serial. These
  identifiers are not cryptographic authentication. Do not expose the port to the
  Internet. Encrypted PUSH modes and biometric synchronization are unsupported.
- Uploads are UTF-8, bounded to 4 MiB, with eight simultaneous requests maximum.
  The receiver binds the selected PC address, not every network interface.
- A changed IP, blocked firewall or occupied port prevents reception. Last contact
  alone means a request arrived; Last saved upload confirms a committed data batch.

Implementation reference: ZKTeco Attendance PUSH Communication Protocol, March 2020,
protocol 2.4.1 (manufacturer manual). Protocol simulation and packaged app tests cover
handshake, commit/retry, duplicate replay, history requests and report compatibility.
Live MB20-VL compatibility must also be checked after pointing the terminal at Oasis.
