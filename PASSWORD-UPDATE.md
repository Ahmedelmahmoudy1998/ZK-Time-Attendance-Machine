# Oasis Attend 1.1.1 — password update

New and edited accounts accept passwords of at least eight characters. Uppercase letters, digits, and symbols are not required. Existing passwords continue to work. Salted password hashing, role checks, and failed-login lockout remain in place.

Validation: all nine core tests passed, including lowercase-only and digits-only eight-character passwords, rejection of seven characters without changing the existing account, and failed-login lockout. The packaged app passed its English/Arabic startup and export smoke check with synthetic data.

This build uses the uploaded desktop source plus the password change. The older VALIDATION.md describes the earlier 1.1.0 release; it does not claim current hardware validation. No live database or user password is included in the source or installer.
