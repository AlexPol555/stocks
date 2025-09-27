from pathlib import Path

path = Path('core/news_pipeline/generators/substring.py')
text = path.read_text(encoding='utf-8')
needle = "        config: PipelineConfig,\n    ) -> Dict[int, CandidateSignal]:"
replacement = "        config: PipelineConfig,\n        **context,\n    ) -> Dict[int, CandidateSignal]:"
if needle in text:
    text = text.replace(needle, replacement)
    path.write_text(text, encoding='utf-8')
else:
    raise SystemExit('signature not found for substring generator')
