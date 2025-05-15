import requests
import os
import json
import re

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
    if response.status_code != 200:
        raise Exception(f"HTTP Error: {response.status_code}, Response: {response.text}")
    if 'errors' in data:
        raise Exception(f"GraphQL Errors: {data['errors']}")
    return data.get('data', {})

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
