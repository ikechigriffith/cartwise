from fastapi import FastAPI

from app.routers.admin_product_selection_reviews import router as admin_product_selection_reviews_router
from app.routers.admin_store_candidates import router as admin_store_candidates_router
from app.routers.compilation import router as compilation_router
from app.routers.health import router as health_router
from app.routers.products import router as products_router
from app.routers.retailers import router as retailers_router
from app.routers.stores import router as stores_router

app = FastAPI(title="Groceries API")

app.include_router(health_router)
app.include_router(products_router)
app.include_router(retailers_router)
app.include_router(stores_router)
app.include_router(admin_store_candidates_router)
app.include_router(admin_product_selection_reviews_router)
app.include_router(compilation_router)
