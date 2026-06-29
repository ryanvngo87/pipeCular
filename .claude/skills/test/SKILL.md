---
description: Run the pytest test suite. Pass a file path or test name to run a subset (e.g. /test tests/utils/test_url_parser.py or /test -k parse_github).
allowed-tools: Bash
---

Run the following command from the project root:

```bash
python -m pytest $ARGUMENTS -v
```

If `$ARGUMENTS` is empty, run the full suite. Report any failures clearly, including the file, test name, and error message.
