# Dead Code and Unused Configuration Audit

This document tracks unused code and configuration that has been removed or is under consideration for removal.

## Removed Configuration Variables

### 1. `S3_BUCKET_NAME` ✅ REMOVED

**Status**: Removed (no S3 operations in codebase)

**Removed from**: `app/core/config.py`

**Reason**: No S3 operations found in codebase. Can be re-added if S3 storage is needed in the future.

**Date Removed**: 2024

### 2. `TEMPLATES_DIR` ✅ REMOVED

**Status**: Removed (unused, directory doesn't exist)

**Removed from**: `app/core/config.py`

**Reason**: No references found in codebase. Directory `./templates` does not exist. Can be re-added if template file storage is needed.

**Date Removed**: 2024

## Current Status

All identified dead code has been removed. The codebase is clean of unused configuration variables.

## Future Considerations

If S3 or template file storage is needed in the future:
- Re-add `S3_BUCKET_NAME` to `app/core/config.py` when implementing S3 features
- Re-add `TEMPLATES_DIR` to `app/core/config.py` when implementing filesystem template loading

