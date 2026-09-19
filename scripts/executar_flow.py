'''Wrapper compatível para pipeline_flow.services.executar_flow.'''

from pipeline_flow.services.executar_flow import *  # noqa: F403
from pipeline_flow.services.executar_flow import main


if __name__ == '__main__':
    raise SystemExit(main())
