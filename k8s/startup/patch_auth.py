#!/usr/bin/env python3
"""Patch AuthMiddleware.dispatch to bypass auth when DISABLE_AUTH=true.
Sets the proper user context (internal user) so endpoints work correctly."""
import sys

target = '/app/backend/app/gateway/auth_middleware.py'
marker = '# DISABLE_AUTH_BYPASS'

with open(target) as f:
    content = f.read()

if marker in content:
    print('[patch_auth] Already patched')
    sys.exit(0)

# Insert our bypass right after the _is_public check inside dispatch()
# We need to come right before "internal_user = None"
# and set the user context properly using internal_user
old = '        internal_user = None\n        if is_valid_internal_auth_token'
new = '''        # DISABLE_AUTH_BYPASS
        import os as _os_auth
        if _os_auth.environ.get('DISABLE_AUTH', '').lower() in ('1', 'true', 'yes'):
            _bypass_user = get_internal_user()
            request.state.user = _bypass_user
            request.state.auth = AuthContext(user=_bypass_user, permissions=_ALL_PERMISSIONS)
            _token = set_current_user(_bypass_user)
            try:
                return await call_next(request)
            finally:
                reset_current_user(_token)
        internal_user = None
        if is_valid_internal_auth_token'''

if old not in content:
    print('[patch_auth] ERROR: could not find insertion point')
    sys.exit(1)

content = content.replace(old, new, 1)

with open(target, 'w') as f:
    f.write(content)

print('[patch_auth] auth_middleware.py dispatch() patched OK with user context')
