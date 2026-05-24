#!/usr/bin/env python3
"""
Patch app/gateway/app.py to add /api/langgraph/* route aliases.
The routers already have full paths like /api/threads, /api/runs etc.
We need to add /api/langgraph/threads, /api/langgraph/runs etc.
Strategy: create alias routes by transforming /api/X -> /api/langgraph/X
"""
import re, sys

target = '/app/backend/app/gateway/app.py'
marker = '# LANGGRAPH_ALIASES_PATCHED'

with open(target) as f:
    content = f.read()

if marker in content:
    print('[patch_app] Already patched')
    sys.exit(0)

lines = content.splitlines(keepends=True)

# Find the line "app = create_app()" at module level
idx = None
for i, l in enumerate(lines):
    if l.strip() == 'app = create_app()':
        idx = i + 1  # insert AFTER this line
        break

if idx is None:
    print('[patch_app] ERROR: app=create_app() not found')
    sys.exit(1)

patch = """
# LANGGRAPH_ALIASES_PATCHED
import re as _re_lg
import importlib as _importlib_lg
import fastapi as _fg_fastapi_lg

def _add_langgraph_aliases(_app):
    _router_modules = [
        'app.gateway.routers.threads',
        'app.gateway.routers.thread_runs',
        'app.gateway.routers.runs',
        'app.gateway.routers.assistants_compat',
        'app.gateway.routers.artifacts',
        'app.gateway.routers.uploads',
        'app.gateway.routers.feedback',
    ]
    _alias_router = _fg_fastapi_lg.APIRouter()
    for _mod_name in _router_modules:
        try:
            _mod = _importlib_lg.import_module(_mod_name)
            _src_router = _mod.router
            for _route in _src_router.routes:
                if not hasattr(_route, 'path'):
                    continue
                # Transform /api/threads/... -> /api/langgraph/threads/...
                _new_path = _re_lg.sub(r'^/api/', '/api/langgraph/', _route.path)
                if _new_path == _route.path:
                    _new_path = '/api/langgraph' + _route.path
                _alias_router.add_api_route(
                    path=_new_path,
                    endpoint=_route.endpoint,
                    methods=list(_route.methods) if _route.methods else ['GET'],
                    response_model=getattr(_route, 'response_model', None),
                    status_code=getattr(_route, 'status_code', 200),
                    tags=list(getattr(_route, 'tags', []) or []),
                    dependencies=list(getattr(_route, 'dependencies', []) or []),
                    name=(_route.name + '_lg') if _route.name else None,
                )
        except Exception as _e:
            import traceback; traceback.print_exc()
            print(f'[patch_app] Warning: failed to alias {_mod_name}: {_e}')
    _app.include_router(_alias_router)

_add_langgraph_aliases(app)
print('[patch_app] /api/langgraph/* aliases added OK')
"""

lines.insert(idx, patch)
with open(target, 'w') as f:
    f.writelines(lines)

print(f'[patch_app] Patched OK after app=create_app() at line {idx}')
