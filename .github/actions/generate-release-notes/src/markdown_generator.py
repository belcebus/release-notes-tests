import os
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

