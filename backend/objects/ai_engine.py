"""
This module provides a simple AI engine built on LangChain + OpenAI.

Notes:
- The OpenAI API key must be set in `.env` as OPENAI_API_KEY.
- Prompts are stored in backend/objects/prompts.
- This engine renders prompt variables and executes the prompt via ChatOpenAI.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Iterable, Optional

from dotenv import find_dotenv, load_dotenv

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover - fallback for older langchain installs
    from langchain.chat_models import ChatOpenAI


_VAR_LINE_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]+)\s*:\s*(.*)$")


class AiEngine:
    def __init__(
        self,
        prompt_dir: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.0,
    ) -> None:
        load_dotenv(find_dotenv())
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment or .env")

        os.environ.setdefault("OPENAI_API_KEY", api_key)
        self.model = model
        self.temperature = temperature
        self.prompt_dir = Path(
            prompt_dir or (Path(__file__).parent / "prompts")
        ).resolve()

        self.llm = ChatOpenAI(model=self.model, temperature=self.temperature)

    def _load_prompt_text(self, prompt_name: str) -> str:
        if not prompt_name.endswith(".txt"):
            prompt_name = f"{prompt_name}.txt"
        prompt_path = self.prompt_dir / prompt_name
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_expected_variables(prompt_text: str) -> Iterable[str]:
        expected = []
        for line in prompt_text.splitlines():
            match = _VAR_LINE_RE.match(line)
            if match:
                expected.append(match.group(1))
        return expected

    @staticmethod
    def _render_prompt(
        prompt_text: str, variables: Dict[str, str]
    ) -> str:
        # Validate required variables (based on "VAR:" lines in the prompt).
        expected = set(AiEngine._extract_expected_variables(prompt_text))
        if expected:
            missing = [
                key for key in expected
                if key not in variables or str(variables[key]).strip() == ""
            ]
            if missing:
                missing_list = ", ".join(sorted(missing))
                raise ValueError(f"Missing variables: {missing_list}")

        rendered_lines = []
        for line in prompt_text.splitlines():
            match = _VAR_LINE_RE.match(line)
            if match and match.group(1) in variables:
                rendered_lines.append(
                    f"{match.group(1)}: {variables[match.group(1)]}"
                )
                continue

            updated_line = line
            for key, value in variables.items():
                pattern = rf"\\b{re.escape(key)}\\b"
                updated_line = re.sub(pattern, str(value), updated_line)
            rendered_lines.append(updated_line)

        return "\n".join(rendered_lines)

    def run_prompt(self, prompt_name: str, variables: Dict[str, str]) -> str:
        prompt_text = self._load_prompt_text(prompt_name)
        rendered_prompt = self._render_prompt(prompt_text, variables)

        if hasattr(self.llm, "invoke"):
            response = self.llm.invoke(rendered_prompt)
            return response.content if hasattr(response, "content") else str(response)

        # Fallback for older langchain versions
        if hasattr(self.llm, "predict"):
            return self.llm.predict(rendered_prompt)

        raise RuntimeError("LangChain ChatOpenAI client does not support invoke/predict.")


"""if __name__ == "__main__":
    engine = AiEngine()
    output = engine.run_prompt(
        "monthly_figures.txt",
        {
            "GIVEN_MONTH": "April",
            "FIELD_OF_EXCELLENCE": "Sports",
        },
    )
    print(output)"""
