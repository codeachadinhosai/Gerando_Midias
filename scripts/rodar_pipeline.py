'''Wrapper compatível para pipeline_flow.cli.'''

from pipeline_flow.cli import *  # noqa: F403
from pipeline_flow.cli import main


if __name__ == '__main__':
    raise SystemExit(main())
