Implement records.py with commands translate PATH and total PATH ACCOUNT.
PATH is a UTF-8 JSON file. Format 1 is {"entries":[{"account":string,"cents":integer},...]}.
Format 2 is {"version":2,"accounts":{account:[integer,...]}}. Preserve the order
of each account's entries. translate replaces a format-1 file with format 2,
printing migrated. On format 2, print current and leave its bytes untouched.
total prints the account's integer sum followed by a newline, or 0 if missing.
It works on both formats and never writes. Extra root keys and malformed
types are invalid. Reject invalid input with exit 2 and preserve its bytes.
Use only the standard library.
