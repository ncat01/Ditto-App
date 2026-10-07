"""Reject synthetic runtime code/assets, including compiled APK contents."""
from pathlib import Path
import argparse
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = (b'DemoCorpus', b'VideoCorpus', b'MockDiscoveryProvider',
             b'MockVerificationAgent', b'MockActionPlanningAgent',
             b'MockFollowUpAgent', b'DemoClock', b'Alex Morgan',
             b'com/ditto/app/data/demo')


def inspect(apk=None):
    failures = []
    source = ROOT / 'android/app/src/main'
    for path in source.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(source).as_posix()
        if '/corpus/' in '/' + relative or 'tutorial_' in path.name:
            failures.append(relative)
        if path.suffix == '.kt' and any(word in path.read_bytes() for word in FORBIDDEN):
            failures.append(relative)
    if apk:
        with zipfile.ZipFile(apk) as archive:
            for name in archive.namelist():
                if name.startswith('assets/corpus/') or 'tutorial_' in name:
                    failures.append(name)
                if re.fullmatch(r'classes\d*\.dex', name):
                    data = archive.read(name)
                    if any(word in data for word in FORBIDDEN):
                        failures.append(name + ': synthetic runtime class/string')
    if failures:
        raise SystemExit('Synthetic runtime guard failed:\n' + '\n'.join(sorted(set(failures))))
    print('Synthetic runtime guard passed' + ('; APK inspected' if apk else '; source inspected'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path)
    inspect(parser.parse_args().apk)
