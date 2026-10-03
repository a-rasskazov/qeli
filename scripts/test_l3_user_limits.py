#!/usr/bin/env python3
"""Q06 static IP, group bandwidth metadata, ACL/source revoke and device caps. Throughput measurement is a separate benchmark."""
from audit_q06_cases import run_cases

if __name__ == "__main__":
    run_cases(__doc__, ('users-live', 'users-policy'))
