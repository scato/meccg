import time

from meccg.medea import Session

if __name__ == '__main__':
    start = time.perf_counter()

    scripts = [
        'var/process/extract.mql',
        'var/process/transform.mql',
        'var/process/load.mql',
        'var/process/verify.mql',
    ]

    session = Session()
    for script in scripts:
        with open(script, encoding='UTF-8') as fp:
            print(f'Executing {script}...')
            result = session.query(''.join(fp.readlines()))

    if result is not None:
        for record in result:
            print(record)

    stop = time.perf_counter()

    print(f'Elapsed time: {stop - start} seconds')
