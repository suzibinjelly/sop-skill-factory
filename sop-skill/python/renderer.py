#!/usr/bin/env python3
"""renderer.py - Render Jinja2 templates with extracted JSON data to produce SKILL.md output.

CLI:
    python renderer.py --input <phase4_extract.json> --template <type> --output <output_path>
    python renderer.py --cleanup  # Delete .sop-temp/ directory

Exit codes: 0=success, 1=business error, 2=JSON error, 3=IO/permission error.
"""

import argparse
import json
import os
import shutil
import sys

from jinja2 import Environment, FileSystemLoader, TemplateError


def get_template_dir():
    """Return the templates/ directory sibling to this script's parent."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
    )


def load_input_json(path):
    """Load and return the input JSON data. Exits with code 2 on JSON errors."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"JSON error in {path}: {e}", file=sys.stderr)
        sys.exit(2)
    except (IOError, PermissionError) as e:
        print(f"IO error reading {path}: {e}", file=sys.stderr)
        sys.exit(3)


def build_template_context(data):
    """Flatten data.metadata and merge with the remaining data fields.

    - metadata.name   -> name
    - metadata.description -> description
    - all other data fields passed as-is
    """
    context = {}

    metadata = data.get("metadata", {})
    context["name"] = metadata.get("name", "")
    context["description"] = metadata.get("description", "")

    for key, value in data.items():
        if key == "metadata":
            continue
        context[key] = value

    return context


def render_template(template_type, context):
    """Load and render the Jinja2 template for the given type.

    Returns the rendered Markdown string.
    Exits with code 1 if the template file doesn't exist or rendering fails.
    """
    template_dir = get_template_dir()
    template_filename = f"{template_type}.md.j2"
    template_path = os.path.join(template_dir, template_filename)

    if not os.path.isfile(template_path):
        print(
            f"Template not found: {template_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    try:
        template = env.get_template(template_filename)
    except TemplateError as e:
        print(f"Jinja2 template load error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        rendered = template.render(**context)
    except TemplateError as e:
        print(f"Jinja2 rendering error: {e}", file=sys.stderr)
        sys.exit(1)

    return rendered


def write_output(path, content):
    """Write rendered content to the output file. Exits with code 3 on IO errors."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except (IOError, PermissionError) as e:
        print(f"IO error writing {path}: {e}", file=sys.stderr)
        sys.exit(3)


def cleanup(output_path):
    """Delete the .sop-temp/ directory in the parent directory of output_path."""
    parent_dir = os.path.dirname(os.path.abspath(output_path))
    sop_temp_dir = os.path.join(parent_dir, ".sop-temp")

    if os.path.isdir(sop_temp_dir):
        try:
            shutil.rmtree(sop_temp_dir)
        except (IOError, PermissionError) as e:
            print(f"IO error cleaning up {sop_temp_dir}: {e}", file=sys.stderr)
            sys.exit(3)


def main():
    parser = argparse.ArgumentParser(
        description="Render Jinja2 templates with extracted JSON data"
    )

    parser.add_argument("--input", help="Path to phase4_extract.json input file")
    parser.add_argument("--template", help="Template type (e.g., sequential)")
    parser.add_argument("--output", help="Output file path for rendered Markdown")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete .sop-temp/ directory and exit",
    )

    args = parser.parse_args()

    # --cleanup works standalone
    if args.cleanup:
        # Use --output to locate .sop-temp/, fall back to CWD
        output_path = args.output or os.getcwd()
        cleanup(output_path)
        sys.exit(0)

    # For normal render mode, all three arguments are required
    missing = []
    if not args.input:
        missing.append("--input")
    if not args.template:
        missing.append("--template")
    if not args.output:
        missing.append("--output")

    if missing:
        print(
            f"Missing required arguments for render mode: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load input JSON
    raw = load_input_json(args.input)

    # Extract the data section
    data = raw.get("data", raw)

    # Build template context by flattening metadata
    context = build_template_context(data)

    # Render the template
    rendered = render_template(args.template, context)

    # Write output
    write_output(args.output, rendered)

    print(f"Rendered output written to {args.output}")
    sys.exit(0)


if __name__ == "__main__":
    main()
