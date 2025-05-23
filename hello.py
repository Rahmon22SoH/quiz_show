from app import create_app, celery
from app.extensions import db
from app.models import User, Role
import os

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """
    Создает контекст для Flask shell.  Позволяет удобно работать с приложением
    в интерактивном режиме (например, через `flask shell`).
    """
    return {
        'app': app,
        'db': db,
        'User': User,
        'Role': Role,
        
    }

if __name__ == '__main__':
    app.run(debug=True)
