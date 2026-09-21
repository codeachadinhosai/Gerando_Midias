'''Wrapper compativel para pipeline_flow.services.migrar_estados.'''

from pipeline_flow.services.migrar_estados import *  # noqa: F403
from pipeline_flow.services.migrar_estados import main


if __name__ == '__main__':
    raise SystemExit(main())
