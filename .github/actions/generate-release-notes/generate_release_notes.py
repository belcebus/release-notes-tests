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

def github_graphql(query, variables, token):
    """
    Realiza una consulta GraphQL a la API de GitHub.
    :param query: La consulta GraphQL a ejecutar.
    :type query: str
    :param variables: Las variables para la consulta GraphQL.
    :type variables: dict
    :param token: El token de acceso para autenticar la solicitud.
    :type token: str
    :return: La respuesta de la API de GitHub.
    :rtype: dict
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    response = requests.post(
        'https://api.github.com/graphql',
        json={'query': query, 'variables': variables},
        headers=headers
    )
    data = response.json()
    if 'errors' in data:
        raise Exception(data['errors'])
    return data['data']

def get_project_id(project_type, owner, project_number, token):
    """
    Obtiene el ID global del proyecto a partir del tipo, owner y número.
    """
    query = '''
    query($login: String!, $number: Int!) {
      %s(login: $login) {
        projectV2(number: $number) {
          id
        }
      }
    }
    ''' % ('user' if project_type == 'users' else 'organization')
    variables = {'login': owner, 'number': project_number}
    data = github_graphql(query, variables, token)
    node = data['user' if project_type == 'users' else 'organization']
    if not node or not node['projectV2']:
        raise Exception('No se encontró el proyecto con esos datos.')
    return node['projectV2']['id']

def get_project_fields(project_id, token):
    """
    Obtiene los campos del proyecto y devuelve un diccionario con los IDs de los campos relevantes.
    """
    query = '''
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              __typename
              ... on ProjectV2FieldCommon {
                id
                name
                dataType
              }
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    '''
    variables = {'projectId': project_id}
    data = github_graphql(query, variables, token)
    fields = data['node']['fields']['nodes']

    # Buscar los campos relevantes por nombre
    field_ids = {}
    for field in fields:
        if field.get('name') == 'Version':
            field_ids['version'] = field['id']
            # Guardar opciones de versión si las necesitas para hacer filtrado
            field_ids['version_options'] = field.get('options', [])
        elif field.get('name') == 'Status':
            field_ids['status'] = field['id']
        elif field.get('name') == 'Linked pull requests':
            field_ids['linked_prs'] = field['id']
    return field_ids


# Ejemplo de uso:
if __name__ == '__main__':
    inputs = get_inputs()
    token = os.environ.get('TOKEN')
    if not token:
        write_error_to_summary("Error: TOKEN no está definido en el entorno.")
        sys.exit(1)
    try:
        project_id = get_project_id(
            inputs['project_type'],
            inputs['owner'],
            inputs['project_number'],
            token
        )
        print("ID del proyecto:", project_id)
    except Exception as e:
        write_error_to_summary(f"Error al obtener el ID del proyecto: {e}")
        sys.exit(1)
    try:
        field_ids = get_project_fields(project_id, token)
        print("IDs de campos relevantes:", field_ids)
    except Exception as e:
        write_error_to_summary(f"Error al obtener los campos del proyecto: {e}")
        sys.exit(1)
