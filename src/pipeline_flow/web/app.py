'''Aplicação FastAPI local com consultas e operações confirmadas.'''

from __future__ import annotations

import argparse
import json
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pipeline_flow.config import load_config
from pipeline_flow.domain import PipelineConfig

from .operations import (
    MAX_UPLOAD_BYTES,
    OperationConflict,
    OperationError,
    PipelineOperations,
)
from .queries import PipelineReadModel, ReadModelError


WEB_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = WEB_ROOT / 'static'
INDEX_FILE = WEB_ROOT / 'templates' / 'index.html'
MEDIA_EXTENSIONS = {
    '.gif', '.jpeg', '.jpg', '.mkv',
    '.mov', '.mp4', '.png', '.webm', '.webp',
}


def _is_loopback(host: str) -> bool:
    if host.lower() == 'localhost':
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def _origin_is_local(origin: str, port: int) -> bool:
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme == 'http'
            and parsed.hostname is not None
            and _is_loopback(parsed.hostname)
            and parsed.port == port
            and not parsed.username
            and not parsed.password
        )
    except (TypeError, ValueError):
        return False


def create_app(config: PipelineConfig | None = None) -> FastAPI:
    resolved = config or load_config(Path.cwd())
    model = PipelineReadModel(resolved)
    operations = PipelineOperations(resolved)
    app = FastAPI(
        title='Pipeline Flow local',
        version='0.1.0',
        description='Backend local com consultas e operações confirmadas.',
    )
    app.mount('/static', StaticFiles(directory=STATIC_ROOT), name='static')

    def require_confirmation(value: str | None) -> None:
        if value != 'confirmar':
            raise HTTPException(
                status_code=400,
                detail='Confirmação explícita ausente.',
            )

    async def limited_body(
        request: Request,
        limit: int,
        too_large_detail: str,
    ) -> bytes:
        declared = request.headers.get('content-length')
        try:
            declared_size = int(declared) if declared is not None else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail='Content-Length inválido.') from exc
        if declared_size is not None and declared_size < 0:
            raise HTTPException(status_code=400, detail='Content-Length inválido.')
        if declared_size is not None and declared_size > limit:
            raise HTTPException(status_code=413, detail=too_large_detail)
        chunks = []
        received = 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > limit:
                raise HTTPException(status_code=413, detail=too_large_detail)
            chunks.append(chunk)
        return b''.join(chunks)

    async def upload_body(request: Request) -> bytes:
        return await limited_body(
            request,
            MAX_UPLOAD_BYTES,
            'Upload acima de 50 MiB.',
        )

    async def json_body(request: Request) -> dict:
        limit = 8 * 1024
        content = await limited_body(
            request,
            limit,
            'Corpo JSON muito grande.',
        )
        try:
            payload = json.loads(content.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail='JSON inválido.') from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail='O corpo deve ser um objeto JSON.')
        return payload

    def operation_result(callback):
        try:
            return callback()
        except OperationConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (OperationError, OSError, ValueError, KeyError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.middleware('http')
    async def security_headers(request, call_next):
        origin = request.headers.get('origin')
        cross_site = request.headers.get('sec-fetch-site') == 'cross-site'
        if cross_site or (origin and not _origin_is_local(origin, resolved.web_port)):
            response = JSONResponse(
                status_code=403,
                content={'detail': 'Origem externa bloqueada.'},
            )
        else:
            response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "media-src 'self'; "
            "style-src 'self'; "
            "script-src 'self'; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-ancestors 'none'"
        )
        return response

    @app.get('/', response_class=HTMLResponse, include_in_schema=False)
    def index():
        return HTMLResponse(INDEX_FILE.read_text(encoding='utf-8'))

    @app.get('/api/health')
    def health():
        return {
            'status': 'ok',
            'consultas_somente_leitura': True,
            'operacoes_confirmadas': True,
            'host_configurado': resolved.web_host,
        }

    @app.get('/api/dashboard')
    def dashboard():
        return model.dashboard()

    @app.get('/api/productions')
    def productions():
        return model.productions()

    @app.get('/api/productions/{production_id}')
    def production(production_id: str):
        try:
            return model.production(production_id)
        except ReadModelError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get('/api/clips')
    def clips(production_id: str | None = None):
        return {'clipes': model.clips(production_id)}

    @app.get('/api/deliveries')
    def deliveries():
        return model.deliveries()

    @app.get('/api/logs')
    def logs(limit: int = Query(default=100, ge=1, le=500)):
        return model.logs(limit)

    @app.get('/api/operations')
    def operation_catalog():
        return operation_result(operations.catalog)

    @app.get('/api/operations/executions')
    def execution_catalog():
        return operations.execution_catalog()

    @app.get('/api/operations/package-latest', response_class=FileResponse)
    def latest_ai_package():
        package = resolved.output_dir / 'pacotes_ia' / 'ULTIMO_PACOTE_IA.zip'
        if not package.is_file():
            raise HTTPException(status_code=404, detail='Pacote consolidado não encontrado.')
        return FileResponse(
            package,
            media_type='application/zip',
            filename='ULTIMO_PACOTE_IA.zip',
        )

    @app.post('/api/operations/prepare')
    def prepare_packages(
        confirmation: str | None = Header(
            default=None, alias='X-Pipeline-Confirmation'
        ),
    ):
        require_confirmation(confirmation)
        return operation_result(operations.prepare_packages)

    @app.post('/api/operations/import')
    def import_saved_response(
        package_id: str = Query(min_length=3, max_length=180),
        response_id: str = Query(min_length=3, max_length=240),
        confirmation: str | None = Header(
            default=None, alias='X-Pipeline-Confirmation'
        ),
    ):
        require_confirmation(confirmation)
        return operation_result(
            lambda: operations.import_saved(package_id, response_id)
        )

    @app.post('/api/operations/import-upload')
    async def import_uploaded_response(
        request: Request,
        package_id: str = Query(min_length=3, max_length=180),
        filename: str = Query(min_length=1, max_length=180),
        confirmation: str | None = Header(
            default=None, alias='X-Pipeline-Confirmation'
        ),
    ):
        require_confirmation(confirmation)
        content = await upload_body(request)
        return operation_result(
            lambda: operations.import_uploaded(package_id, filename, content)
        )

    @app.post('/api/operations/register-image')
    async def register_image(
        request: Request,
        production_id: str = Query(min_length=1, max_length=120),
        revision: str = Query(min_length=16, max_length=16),
        clip_id: str = Query(min_length=1, max_length=180),
        filename: str = Query(min_length=1, max_length=180),
        confirmation: str | None = Header(
            default=None, alias='X-Pipeline-Confirmation'
        ),
    ):
        require_confirmation(confirmation)
        content = await upload_body(request)
        return operation_result(
            lambda: operations.register_image(
                production_id, revision, clip_id, filename, content
            )
        )

    @app.post('/api/operations/review-image')
    async def review_image(
        request: Request,
        confirmation: str | None = Header(
            default=None, alias='X-Pipeline-Confirmation'
        ),
    ):
        require_confirmation(confirmation)
        payload = await json_body(request)
        return operation_result(
            lambda: operations.review_image(
                payload.get('production_id'),
                payload.get('revision'),
                payload.get('clip_id'),
                payload.get('decision'),
                payload.get('image_sha256'),
                payload.get('reason', ''),
            )
        )

    @app.post('/api/operations/generate-carousel')
    async def generate_carousel(
        request: Request,
        confirmation: str | None = Header(
            default=None, alias='X-Pipeline-Confirmation'
        ),
    ):
        require_confirmation(confirmation)
        payload = await json_body(request)
        return operation_result(
            lambda: operations.generate_carousel(
                payload.get('production_id'),
                payload.get('revision'),
                payload.get('clip_id'),
                payload.get('image_sha256'),
                payload.get('regenerate', False),
            )
        )

    @app.post('/api/operations/generate-video', status_code=202)
    async def generate_video(
        request: Request,
        confirmation: str | None = Header(
            default=None, alias='X-Pipeline-Confirmation'
        ),
    ):
        require_confirmation(confirmation)
        payload = await json_body(request)
        return operation_result(
            lambda: operations.start_video(
                payload.get('production_id'),
                payload.get('revision'),
                payload.get('clip_id'),
                payload.get('image_sha256'),
                payload.get('credit_confirmation'),
            )
        )

    @app.get(
        '/media/{scope}/{relative_path:path}',
        response_class=FileResponse,
        include_in_schema=False,
    )
    def media(scope: str, relative_path: str):
        roots = {
            'preparados': resolved.output_dir,
            'entregas': resolved.delivery_dir,
        }
        root = roots.get(scope)
        if root is None:
            raise HTTPException(status_code=404, detail='Mídia não encontrada.')
        candidate = (root / relative_path).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail='Mídia não encontrada.') from exc
        if (
            candidate.suffix.lower() not in MEDIA_EXTENSIONS
            or not candidate.is_file()
        ):
            raise HTTPException(status_code=404, detail='Mídia não encontrada.')
        return FileResponse(candidate)

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raiz', type=Path, default=Path.cwd())
    args = parser.parse_args()
    config = load_config(args.raiz)
    if not _is_loopback(config.web_host):
        parser.error('WEB_HOST deve apontar para localhost ou um endereço loopback.')
    try:
        import uvicorn
    except ImportError as exc:
        parser.error(f'Uvicorn não está instalado: {exc}')
    uvicorn.run(
        create_app(config),
        host=config.web_host,
        port=config.web_port,
        log_level='info',
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
