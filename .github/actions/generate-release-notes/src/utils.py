import sys
import os
import argparse
import re

def write_error_to_summary(message):
    """
    Escribe un mensaje de error en el resumen de la acción de GitHub y por la salida estándar.
    :param message: El mensaje de error a escribir.
    :type message: str
    :return: None
    :rtype: None
    """
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_file:
        try:
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write(f"❌ {message}\n")
        except Exception as e:
            print(f"Error al escribir en el summary: {e}", file=sys.stderr)
    print(message, file=sys.stderr)

def get_inputs():
    """
    Obtiene y valida los inputs de la acción de GitHub o de la línea de comandos.
    """
    # Si se ejecuta localmente, usa argparse
    if sys.stdin.isatty():
        parser = argparse.ArgumentParser(description='Generar release notes desde un GitHub Project.')
        parser.add_argument('--project-url', required=False, help='URL del tablero de GitHub Projects')
        parser.add_argument('--version', required=False, help='Versión a filtrar')
        parser.add_argument('--token', required=False, help='GitHub Token')
        args = parser.parse_args()

        project_url = args.project_url or os.environ.get('INPUT_PROJECT_URL')
        version = args.version or os.environ.get('INPUT_VERSION')
        token = args.token or os.environ.get('TOKEN')
    else:
        project_url = os.environ.get('INPUT_PROJECT_URL')
        version = os.environ.get('INPUT_VERSION')
        token = os.environ.get('TOKEN')

    if not project_url:
        write_error_to_summary("Error: INPUT_PROJECT_URL no está definido.")
        sys.exit(1)
    if not version:
        write_error_to_summary("Error: INPUT_VERSION no está definido.")
        sys.exit(1)
    if not token:
        write_error_to_summary("Error: TOKEN no está definido.")
        sys.exit(1)

    match = re.match(r'https://github\.com/(users|orgs)/([^/]+)/projects/(\d+)', project_url)
    if not match:
        write_error_to_summary("Error: INPUT_PROJECT_URL no tiene el formato correcto.")
        write_error_to_summary("Formato esperado: https://github.com/{users|orgs}/{owner}/projects/{project_number}")
        sys.exit(1)

    project_type = match.group(1)
    owner = match.group(2)
    project_number = int(match.group(3))

    inputs = [
        ("Project URL", project_url),
        ("Version", version),
        ("Project Type", project_type),
        ("Owner", owner),
        ("Project Number", project_number)
    ]
    max_label_length = max(len(label) for label, _ in inputs)
    for label, value in inputs:
        print(f"\033[92m{label.ljust(max_label_length)}:\033[0m {value}")

    return {
        'project_url': project_url,
        'version': version,
        'project_type': project_type,
        'owner': owner,
        'project_number': project_number,
        'token': token
    }
