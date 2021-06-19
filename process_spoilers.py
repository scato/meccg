import re
import time

from meccg.medea import Session

if __name__ == '__main__':
    start = time.perf_counter()

    # increase regular expression cache size
    # there are a lot of patterns in var/regex/text.hazard-event.txt, so the default 512 won't suffice
    re._MAXCACHE = 1024

    scripts = [
        'var/process/extract.mql',
        'var/process/transform.mql',
        'var/process/load.mql',
        'var/process/verify.mql',
        # 'var/process/missing.mql',
    ]

    session = Session()
    for script in scripts:
        with open(script, encoding='UTF-8') as fp:
            print(f'Executing {script}...')
            result = session.query(''.join(fp.readlines()))

    if result is not None:
        num_results = 0
        for record in result:
            num_results += 1
            print(record)

        print(f'Number of results: {num_results}')

    stop = time.perf_counter()

    print(f'Elapsed time: {stop - start} seconds')
