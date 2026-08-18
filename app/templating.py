from fastapi.templating import Jinja2Templates

from app.paths import resource_path

templates = Jinja2Templates(directory=resource_path("app", "templates"))
