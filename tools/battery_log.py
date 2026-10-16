"""Append complete JSON records and rotate under the same process lock."""
import argparse
import fcntl
import gzip
import json
import os
from pathlib import Path
import re
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', type=Path, default=Path('/config/battery_algorithm.log'))
    parser.add_argument('--rotate')
    args = parser.parse_args()
    payload = None
    if args.rotate:
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', args.rotate):
            parser.error('rotation label must be YYYY-MM')
    else:
        # Validate before opening the log; user text never becomes a shell command.
        payload = (json.dumps(json.load(sys.stdin), ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    with open(str(args.path) + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.rotate:
            archive = args.path.with_name(f'{args.path.stem}-{args.rotate}.log.gz')
            if archive.exists():
                raise FileExistsError(f'Refusing to overwrite {archive}')
            # Keep the original intact if compression fails.
            temporary = Path(str(archive) + '.tmp')
            try:
                with args.path.open('rb') as source, gzip.open(temporary, 'wb') as output:
                    while chunk := source.read(1024 * 1024):
                        output.write(chunk)
                os.replace(temporary, archive)
                args.path.write_bytes(b'')
            finally:
                temporary.unlink(missing_ok=True)
        else:
            with args.path.open('ab', buffering=0) as output:
                view = memoryview(payload)
                while view:
                    view = view[output.write(view):]


if __name__ == '__main__':
    main()
