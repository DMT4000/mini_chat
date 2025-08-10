import yaml, json, pathlib, datetime
from langchain.prompts import PromptTemplate

# Look for prompts in the same directory as this file
ROOT = pathlib.Path(__file__).resolve().parent / "prompts"

class PromptRegistry:
    def __init__(self, root: pathlib.Path = ROOT):
        self.root = root

    def get(self, name: str, **params) -> str:
        path = self.root / f"{name}.yaml"
        with open(path) as f:
            raw = yaml.safe_load(f)["template"]
        return PromptTemplate.from_template(raw).format(**params)

    def list(self):
        return [p.stem for p in self.root.glob("*.yaml")]

    def add(self, name: str, template: str):
        data = {"template": template, "created": datetime.datetime.utcnow().isoformat()}
        (self.root / f"{name}.yaml").write_text(yaml.dump(data))
