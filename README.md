# release-notes-tests
Test repository to test release notes automation creation

## Ejecución local
Para ejecutar el script de release notes localmente, sigue estos pasos:

1. **Crea y activa un entorno virtual de Python** (recomendado):

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2. **Instala las dependencias usando el fichero `requirements.txt`**:

    ```bash
    pip install -r .github/actions/generate-release-notes/requirements.txt
    ```

3. **Ejecuta el script usando argumentos por línea de comandos**:

    ```bash
    python .github/actions/generate-release-notes/generate_release_notes.py \
      --project-url https://github.com/users/belcebus/projects/1 \
      --version v1.0.0 \
      --token ghp_tu_token_personal
    ```

    Si no pasas algún argumento, el script intentará obtenerlo de las variables de entorno correspondientes.

4. **Nota sobre el summary**:

    Si quieres simular la escritura en el summary, puedes exportar la variable antes de ejecutar el script:

    ```bash
    export GITHUB_STEP_SUMMARY=tu_summary_aquí
    ```
