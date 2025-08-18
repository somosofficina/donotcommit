from http import HTTPStatus
from pathlib import Path
from typing import Final

import logfire
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from src.settings import settings
from src.templates_conf import templates

app = FastAPI(title='donotcommit.com')
app.mount('/static', StaticFiles(directory='src/static'), name='static')

logfire.configure(
    token=settings.LOGFIRE_TOKEN, send_to_logfire='if-token-present'
)
logfire.instrument_fastapi(app, capture_headers=True)
logfire.instrument_system_metrics()

PROJECT_ROOT: Final = Path(__file__).parent.parent
GITIGNORE_FOLDER: Final = PROJECT_ROOT / 'gitignore'
TEMPLATES: Final = tuple(GITIGNORE_FOLDER.rglob('*.gitignore'))


@app.get('/', response_class=HTMLResponse, include_in_schema=False)
def read_root(request: Request):
    return templates.TemplateResponse(
        'index.html', context={'request': request}
    )


@app.get('/api/list', response_class=PlainTextResponse)
def list_templates():
    """
    Lists all available gitignore templates by github.com/github/gitignore
    """
    language_names = sorted([
        Path(file).name.lower().removesuffix('.gitignore')
        for file in TEMPLATES
    ])

    formatted_names = ',\n'.join(
        ','.join(language_names[i : i + 5])
        for i in range(0, len(language_names), 5)
    )

    return formatted_names


@app.get('/api/{templates}', response_class=PlainTextResponse)
def get_template(templates: str):
    """
    Return gitignore content with all the languages.
    The template names should be passed in lower case, no spaces, and comma
    separated.

    To get all available templates, make a request to `/api/list`

    Example:
        `https://donotcommit.com/api/python,lua,zig`
    """
    templates = templates.strip(', ')
    templates_names = [name.strip() for name in templates.split(',')]

    gitignore_response = ''
    for template in templates_names:
        found_template = tuple(
            GITIGNORE_FOLDER.rglob(
                f'{template}.gitignore', case_sensitive=False
            )
        )

        if not found_template:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f'Template "{template}" not found.',
            )

        template_content = Path(found_template[0]).read_text(encoding='utf-8')
        content = f'## {template.capitalize()}\n\n{template_content}\n'
        gitignore_response += content

    return gitignore_response.strip()
