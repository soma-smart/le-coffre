from fastapi import FastAPI

from .infra.container import Container
from .infra.api.router import setup_route


container = Container()
container.wire(modules=[setup_route])

app = FastAPI()
app.include_router(setup_route.router)
