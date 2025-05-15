from utils import get_inputs, write_error_to_summary
from github_api import get_project_id, get_project_fields, get_project_items
from markdown_generator import generate_markdown, save_markdown, add_to_summary, update_readme_with_release_notes
import sys
import os

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
    try:
        # Si la ejecución es local hay que utilizar otro path
        if os.environ.get('GITHUB_ACTIONS') != 'true':
            readme_path = os.path.join(os.path.dirname(__file__), '..', '..', '..','..', 'README.md')
        else:
            readme_path = os.path.join(os.path.dirname(__file__), '..', 'README.md')
        update_readme_with_release_notes(readme_path, filename)
    except Exception as e:
        write_error_to_summary(f"Error al actualizar el README: {e}")
        sys.exit(1)
    print("\033[92mProceso completado con éxito.\033[0m")
    sys.exit(0)