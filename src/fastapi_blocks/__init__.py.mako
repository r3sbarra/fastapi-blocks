from fastapi import APIRouter

% if template_routers:
# Import Template Routers
% for name, module in template_routers.items():
from ${module} import router as ${name}
% endfor
# === Template Routers End
% endif

% if api_routers:
# Import API Routers
% for name, module in api_routers.items():
from ${module} import router as ${name}
% endfor
# === API Routers End
% endif

# Template Router
template_router = APIRouter()

% if template_routers:
% for name, module in template_routers.items():
template_router.include_router(${name})
% endfor
% endif

# API Router
api_router = APIRouter()

% if api_routers:
% for name, module in api_routers.items():
api_router.include_router(${name})
% endfor
% endif