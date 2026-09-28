# Company details — Oasis Attend 1.1.2

Sign in as an administrator, open **Settings → Company details**, enter the company name and branch, choose a PNG or JPEG logo, and select **Save**. Use **Remove logo** and then **Save** to remove it. All three values are optional.

These settings are stored in the selected attendance database, including the image itself. Each database can have different company details. Backups retain them, and moving the original image file does not break reports. Opening an existing database adds the settings table automatically without changing employee or attendance records.

The company name, branch and logo appear on login, the main screen, and PDF, XLS, XLSX and print-preview reports, including attendance reports. CSV exports include the company and branch as text before the data header; CSV cannot store images. If you import these CSV files into another system, account for the additional metadata rows. With all company details empty, reports retain the existing product branding.

Logos are limited to PNG/JPEG files up to 5 MB and 16 million pixels. They are resized proportionally and stored as PNG. Company and branch names support Arabic and English, with up to 160 characters each.

Validation uses synthetic data: company setting persistence, backup and removal, administrator permissions, invalid input and transaction rollback, export identity/image embedding, spreadsheet formula and HTML escaping, and bilingual application smoke checks. No production database, logo or account credentials are included in the source or installer.
