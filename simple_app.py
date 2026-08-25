"""WSGI and local-development entrypoint for Ayah App."""

from ayah_app import create_app
import config

app = create_app()

if __name__ == "__main__":
    app.run(debug=config.DEBUG_MODE, host=config.HOST, port=config.PORT)
