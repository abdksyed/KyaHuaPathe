import jinja2
from typing import Any


class PromptManager:
    def __init__(self):
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader("src/prompts"),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def __call__(self, name: str, **kwargs: Any) -> str:
        template_path = f"{name}.md.j2"
        try:
            template = self.env.get_template(template_path)
            rendered_content = template.render(**kwargs)
            return rendered_content
        except jinja2.exceptions.TemplateNotFound:
            raise ValueError(f"Template {template_path} not found")
