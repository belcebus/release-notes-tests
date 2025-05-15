import os
import re
import sys
import requests
import argparse

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
    Obtiene el ID global y el nombre del tablero (title) a partir del tipo, owner y número.
    """
    query = '''
    query($login: String!, $number: Int!) {
      %s(login: $login) {
        projectV2(number: $number) {
          id
          title
        }
      }
    }
    ''' % ('user' if project_type == 'users' else 'organization')
    variables = {'login': owner, 'number': project_number}
    data = github_graphql(query, variables, token)
    node = data['user' if project_type == 'users' else 'organization']
    if not node or not node['projectV2']:
        raise Exception('No se encontró el proyecto con esos datos.')
    return node['projectV2']['id'], node['projectV2']['title']

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

def get_project_items(project_id, field_ids, version, token):
    """
    Obtiene los items del proyecto y filtra por la versión indicada.
    Devuelve una lista de issues con los campos relevantes.
    """
    # Query para obtener los items del proyecto
    query = '''
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100) {
            nodes {
              content {
                ... on Issue {
                  id
                  number
                  title
                  url
                  labels(first: 10) {
                    nodes {
                      name
                      color
                    }
                  }
                }
              }
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    field {
                      ... on ProjectV2SingleSelectField {
                        id
                        name
                      }
                    }
                    name
                  }
                  ... on ProjectV2ItemFieldPullRequestValue {
                    field {
                      ... on ProjectV2Field {
                        id
                        name
                      }
                    }
                    pullRequests(first: 10) {
                      nodes {
                        number
                        url
                        merged
                        repository {
                          nameWithOwner
                        }
                      }
                    }
                  }
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
    items = data['node']['items']['nodes']

    filtered_issues = []
    for item in items:
        issue = item.get('content')
        if not issue:
            continue

        # Buscar el valor del campo Version para este item
        version_value = None
        status_value = None
        linked_prs = []
        labels = []
        if issue.get('labels') and issue['labels'].get('nodes'):
            labels = [label['name'] for label in issue['labels']['nodes']]
        for field in item['fieldValues']['nodes']:
            # Campo Version
            if (
                field.get('field')
                and field['field'].get('id') == field_ids.get('version')
                and 'name' in field
            ):
                version_value = field['name']
            # Campo Status
            if (
                field.get('field')
                and field['field'].get('id') == field_ids.get('status')
                and 'name' in field
            ):
                status_value = field['name']
            # Campo Linked pull requests
            if (
                field.get('field')
                and field['field'].get('id') == field_ids.get('linked_prs')
                and 'pullRequests' in field
            ):
                for pr in field['pullRequests']['nodes']:
                    linked_prs.append({
                        'number': pr['number'],
                        'url': pr['url'],
                        'merged': pr['merged'],
                        'repo': pr['repository']['nameWithOwner']
                    })

        # Filtrar por versión
        if version_value == version:
            filtered_issues.append({
                'id': issue['id'],
                'number': issue['number'],
                'title': issue['title'],
                'url': issue['url'],
                'status': status_value,
                'linked_prs': linked_prs,
                'labels': labels
            })

    return filtered_issues

def generate_markdown(issues, version, repo_name):
    """
    Genera el contenido markdown para las release notes.
    """
    # Título principal
    md = [f"# {repo_name} - {version}\n"]

    # Sección de lista de mejoras, correcciones y nuevas funcionalidades
    md.append("## Listado de mejoras, correcciones y nuevas funcionalidades\n")

    for issue in issues:
        # Línea principal de la issue
        label_str = f" [labels: {', '.join(issue['labels'])}]" if issue.get('labels') else ""
        md.append(f"- [Issue #{issue['number']}]({issue['url']}): {issue['title']} _(Estado: {issue['status']})_{label_str}")
        # Lista anidada de PRs asociadas
        if issue['linked_prs']:
            for pr in issue['linked_prs']:
                emoji_pr = "✅" if pr['merged'] else "🟡"
                md.append(f"  - [PR #{pr['number']}]({pr['url']}) ({pr['repo']}) {emoji_pr}")
    # Lista de repositorios únicos de las PRs
    repos = sorted({pr['repo'] for issue in issues for pr in issue['linked_prs']})
    if repos:
        md.append("\n## Repositorios asociados a las Pull Requests\n")
        for repo in repos:
            md.append(f"- {repo}")

    return "\n".join(md)

def save_markdown(content, version):
    """
    Guarda el contenido markdown en un archivo.
    """
    filename = f"RELEASE_NOTES_V{version}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\033[92mArchivo markdown generado:\033[0m {filename}")
    return filename

def add_to_summary(content):
    """
    Agrega el contenido al resumen de la acción de GitHub.
    """
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_file:
        with open(summary_file, 'a', encoding='utf-8') as f:
            f.write(content + "\n")

if __name__ == '__main__':
    inputs = get_inputs()
    token = inputs['token'] or os.environ.get('TOKEN')
    if not token:
        write_error_to_summary("Error: TOKEN no está definido en el entorno.")
        sys.exit(1)
    try:
        project_id, project_title = get_project_id(
            inputs['project_type'],
            inputs['owner'],
            inputs['project_number'],
            token
        )
        print(f"\033[92mID del proyecto:\033[0m {project_id}")
        print(f"\033[92mTítulo del proyecto:\033[0m {project_title}")
    except Exception as e:
        write_error_to_summary(f"Error al obtener el ID del proyecto: {e}")
        sys.exit(1)
    try:
        field_ids = get_project_fields(project_id, token)
        print("\033[94mIDs de campos relevantes:\033[0m")
        max_key_length = max(len(k) for k in field_ids.keys())
        for k, v in field_ids.items():
            print(f"\033[92m{k.ljust(max_key_length)}:\033[0m {v}")
    except Exception as e:
        write_error_to_summary(f"Error al obtener los campos del proyecto: {e}")
        sys.exit(1)
    try:
        issues = get_project_items(project_id, field_ids, inputs['version'], token)
        print(f"\033[94mIssues filtradas por versión '{inputs['version']}':\033[0m")
        for issue in issues:
            print(f"- Issue #{issue['number']}: {issue['title']} (Estado: {issue['status']})")
            for pr in issue['linked_prs']:
                estado_pr = "MERGEADA" if pr['merged'] else "ABIERTA"
                print(f"    - PR #{pr['number']} [{estado_pr}]: {pr['repo']} ({pr['url']})")
    except Exception as e:
        write_error_to_summary(f"Error al obtener los items del proyecto: {e}")
        sys.exit(1)
    try:
        markdown = generate_markdown(issues, inputs['version'], project_title)
        filename = save_markdown(markdown, inputs['version'])
        add_to_summary(markdown)
    except Exception as e:
        write_error_to_summary(f"Error al generar el markdown: {e}")
        sys.exit(1)