import os
import re
import sys

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
    Obtiene y valida los inputs de la acción de GitHub.
    Esta función obtiene los inputs de la acción de GitHub desde las variables de entorno.
    Valida que los inputs requeridos estén definidos y en el formato correcto.
    Si algún input no es válido, escribe un mensaje de error en el resumen de la acción
    y termina la ejecución del script.
    :return: Un diccionario con los inputs validados.
    :rtype: dict
    """
    project_url = os.environ.get('INPUT_PROJECT_URL')
    version = os.environ.get('INPUT_VERSION')

    if not project_url:
        write_error_to_summary("Error: INPUT_PROJECT_URL no está definido.")
        sys.exit(1)
    if not version:
        write_error_to_summary("Error: INPUT_VERSION no está definido.")
        sys.exit(1)

    # Validar formato de la URL
    match = re.match(r'https://github\.com/(users|orgs)/([^/]+)/projects/(\d+)', project_url)
    if not match:
        write_error_to_summary("Error: INPUT_PROJECT_URL no tiene el formato correcto.")
        write_error_to_summary("Formato esperado: https://github.com/{users|orgs}/{owner}/projects/{project_number}")
        sys.exit(1)

    # Extraer tipo, owner y número de proyecto
    project_type = match.group(1)
    owner = match.group(2)
    project_number = int(match.group(3))

    return {
        'project_url': project_url,
        'version': version,
        'project_type': project_type,
        'owner': owner,
        'project_number': project_number
    }

# Ejemplo de uso:
if __name__ == '__main__':
    inputs = get_inputs()
    print("Inputs validados correctamente:", inputs)