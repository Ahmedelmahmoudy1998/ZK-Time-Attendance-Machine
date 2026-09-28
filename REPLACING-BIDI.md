# Replaceable python-bidi component

Oasis Attend uses python-bidi 0.6.11 for Arabic PDF text direction. Its LGPL license and source are distributed in THIRD-PARTY-NOTICES.txt and third-party-sources. The component's license takes precedence over the ODS EULA for that component, including modification and debugging rights.

This release uses a folder-based PyInstaller build. The `bidi` package's Python files are collected as files, not into the embedded PYZ archive. You can replace them without rebuilding Oasis Attend.

1. Close Oasis Attend and back up `_internal/bidi` in the portable or installed application directory.
2. Replace `_internal/bidi` with a compatible python-bidi package, preserving the module interface used by `from bidi.algorithm import get_display`.
3. If replacing the extension used by the package initializer, use a binary compatible with the bundled CPython 3.12, Windows x64. A compatible replacement initializer that exposes the pure-Python `algorithm` module also works.
4. Restart the application and export an Arabic PDF to verify your replacement. Restore the backup if necessary.

Build from the included upstream source archive if desired; it contains upstream build instructions and metadata. No signature check, hash allowlist, or integrity check prevents replacement of this package. Reinstalling/updating the application may replace modified component files, so retain a separate copy of your changes.

The installer is an Inno Setup archive that installs this complete folder layout. It does not install a one-file application.
