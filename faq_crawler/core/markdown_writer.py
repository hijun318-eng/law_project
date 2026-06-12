from pathlib import Path


class MarkdownWriter:

    @staticmethod
    def write(
        save_dir,
        filename,
        metadata,
        content
    ):

        save_dir = Path(save_dir)

        filepath = save_dir / filename

        yaml = "---\n"

        for k, v in metadata.items():

            yaml += f'{k}: "{v}"\n'

        yaml += "---\n\n"

        text = yaml + content

        filepath.write_text(
            text,
            encoding="utf-8"
        )

        return filepath