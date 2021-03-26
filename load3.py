from meccg.medea import Session


def execute_mql(filename):
    with open(filename) as fp:
        session = Session()
        session.query(''.join(fp.readlines()))


execute_mql('var/process/atscreat.mql')
