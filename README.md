# release-notes-tests
Test repository to test release notes automation creation

## Ejecución local
Para ejecutar el script de release notes localmente, sigue estos pasos:

1. **Crea un archivo `.env`** (opcional, pero recomendado para no exponer tu token en el terminal):

   ```bash
   TOKEN=ghp_tu_token_personal
   INPUT_PROJECT_URL=https://github.com/users/belcebus/projects/1
   INPUT_VERSION=v1.0.0
   ```

2. **Carga las variables de entorno antes de ejecutar el script**:

    ```bash
    export $(cat .env | xargs)
    python .github/actions/generate-release-notes/generate_release_notes.py
    ```

    O bien, puedes exportarlas manualmente:

    ```bash
    export TOKEN=ghp_tu_token_personal
    export INPUT_PROJECT_URL=https://github.com/users/belcebus/projects/1
    export INPUT_VERSION=v1.0.0
    python .github/actions/generate-release-notes/generate_release_notes.py
    ```

3. **Asegúrate de tener instaladas las dependencias**:

    ```bash
    npm install
    ```

4. **Nota sobre el summary**:

    Si quieres simular la escritura en el summary, puedes exportar también la variable:

    ```bash
    export SUMMARY=tu_summary_aquí
    ```
