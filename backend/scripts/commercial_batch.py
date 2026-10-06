"""Validate, package and optionally stage Ditto with one credential-private command."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def run(*arguments, cwd=ROOT):
    subprocess.run([sys.executable, *arguments], cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', action='store_true', help='Create disabled private Functions and run live probes; never publish.')
    args = parser.parse_args()
    if args.stage and not os.getenv('APPWRITE_DEPLOY_KEY'):
        raise SystemExit('APPWRITE_DEPLOY_KEY is missing. Add it privately to this runner; never paste it in chat.')
    run('-m', 'pip', 'install', '--disable-pip-version-check', 'pip==26.2.1', '-r', 'backend/requirements.txt')
    run('-m', 'pip', 'check')
    run('-m', 'pytest', '-q', cwd=ROOT / 'backend')
    run('backend/scripts/package_appwrite_cloud.py')
    run('backend/scripts/deploy_appwrite_cloud.py', *(['--stage'] if args.stage else []))
    print('Batch complete. No public launch, data migration, billing change or app-store publication was performed.')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError:
        raise SystemExit('Batch stopped at a failed check. Nothing was published; resolve the failed step before retrying.') from None
