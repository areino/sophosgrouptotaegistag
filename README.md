# tagger.py — Sophos Central → Taegis XDR Tag Sync

> ⚠️ **Temporary Workaround — Product Gap**
>
> Taegis XDR and Sophos Central do not currently synchronise asset tags between platforms. This script bridges that gap manually. It should be **decommissioned** once native tag synchronisation is available. Monitor Sophos and Secureworks release notes for both products and retire this script when the feature ships.

---

## What It Does

`tagger.py` synchronises asset tags from **Sophos Central** to **Taegis XDR**:

1. Authenticates to both platforms using OAuth 2.0 client credentials
2. Retrieves all Sophos-managed assets from Taegis XDR (endpoint types `ENDPOINT_SOPHOS` and `ENDPOINT_SOPHOS_CIXA`)
3. For each asset, looks up its tags in Sophos Central using the endpoint's host ID
4. Pushes the first tag found to the corresponding asset in Taegis XDR via GraphQL mutation
5. Skips assets that already have the tag set, and logs assets with no tags defined

All activity is logged to stdout with UTC timestamps.

---

## Prerequisites

- Python 3.x
- The `requests` library:
  ```
  pip install requests
  ```

---

## Configuration

Credentials are stored in `creds.py` in the same directory as `tagger.py`. The file must define the following variables:

```python
# Sophos Central
sophos_tenant_id    = "<your-sophos-tenant-uuid>"
sophos_client_id    = "<your-sophos-client-id>"
sophos_client_secret = "<your-sophos-client-secret>"
sophos_data_region  = "<your-region>"   # e.g. "us03"

# Taegis XDR
taegis_api_endpoint  = "https://api.ctpx.secureworks.com"
taegis_client_id     = "<your-taegis-client-id>"
taegis_client_secret = "<your-taegis-client-secret>"
taegis_tenant_id     = "<your-taegis-tenant-id>"
```

> 🔐 **Security:** `creds.py` contains sensitive secrets. Keep it out of source control — add it to `.gitignore`. Restrict file system permissions so only the service account running the script can read it.

---

## Usage

The script takes no command-line arguments:

```bash
python tagger.py
```

Example output:

```
2025-06-10 07:00:01  Starting tagger process
2025-06-10 07:00:01  Authenticating to Sophos...
2025-06-10 07:00:02  Authenticating to Taegis...
2025-06-10 07:00:02  Getting list of Taegis assets
2025-06-10 07:00:03  -- Retrieved 142 Sophos assets from Taegis
2025-06-10 07:00:03  Getting tags for corresponding assets in Sophos Central
2025-06-10 07:00:03  -- Set tag [finance] for asset abc-123 - DESKTOP-FINANCE01
2025-06-10 07:00:04  -- Skipped, already set - DESKTOP-FINANCE02
2025-06-10 07:00:04  -- No tags defined for asset xyz-456 - LAPTOP-HR01
```

---

## Scheduled Execution

The script is designed to run periodically — once per day is recommended.

### Windows Task Scheduler

1. Open **Task Scheduler** → **Create Basic Task**
2. Set the trigger to **Daily** at your preferred time
3. Set the action to:
   - **Program:** `python`
   - **Arguments:** `tagger.py`
   - **Start in:** `C:\git\tagger`

### Linux / macOS (cron)

```cron
0 6 * * * cd /path/to/tagger && python tagger.py >> /var/log/tagger.log 2>&1
```

Runs daily at 06:00, appending output to a log file.

---

## Limitations

- Only the **first tag** on each Sophos Central asset is synced to Taegis. If an asset has multiple tags in Sophos Central, the remaining tags are ignored.
- Sync is **one-way only**: Sophos Central → Taegis XDR. Tags added directly in Taegis are not affected.
- If the Taegis API returns a 429 rate-limit response, the script exits immediately rather than retrying. Re-run it after a short delay if this occurs.

---

## Files

| File | Description |
|---|---|
| `tagger.py` | Main sync script |
| `creds.py` | API credentials — **do not commit to source control** |
| `README.md` | This file |
