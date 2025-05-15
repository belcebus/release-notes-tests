import os
import re

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
    filename = f"RELEASE_NOTES_{version}.md"
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

import os
import re

def update_readme_with_release_notes(readme_path, release_notes_filename):
    """
    Añade (si no existe) un enlace a la release notes en la sección '## Release Notes' del README.
    """
    # Enlace relativo a añadir
    new_link = f"- [{release_notes_filename}](./{release_notes_filename})"

    # Leer el README
    if not os.path.exists(readme_path):
        print(f"README no encontrado en {readme_path}")
        return

    with open(readme_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Buscar la sección '## Release Notes'
    section_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower() == "## release notes":
            section_idx = i
            break

    if section_idx is None:
        # Añadir la sección al final
        lines.append("\n## Release Notes\n")
        lines.append("\n")
        lines.append(f"{new_link}\n")
    else:
        # Buscar la lista bajo la sección
        insert_idx = section_idx + 1
        # Saltar líneas en blanco tras el título
        while insert_idx < len(lines) and lines[insert_idx].strip() == "":
            insert_idx += 1

        # Buscar si ya hay una lista
        list_start = insert_idx
        while list_start < len(lines) and lines[list_start].strip().startswith("- "):
            if lines[list_start].strip() == new_link:
                print("El enlace de la release notes ya existe en el README.")
                return
            list_start += 1

        # Insertar el nuevo enlace en la lista o crear la lista si no existe
        lines.insert(list_start, f"{new_link}\n")

    # Escribir el README actualizado
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"\033[92mREADME.md actualizado con el enlace a la nueva release notes.\033[0m")