import os
import sys

from fastapi_starter import __version__
from fastapi_starter.templates import get_all_templates


def print_banner():
    banner = f"""
========================================================================
           🚀 Hitesh FastAPI Starter CLI (v{__version__})
   Production-ready, Modular Microservices Scaffold Generator
========================================================================
"""
    print(banner)


def create_project_cli():
    if len(sys.argv) < 2:
        print_banner()
        print("❌ Usage: fastapi-starter <project_name>")
        print("          hitesh-fastapi-starter <project_name>\n")
        print("Example:  fastapi-starter my-app")
        sys.exit(1)

    arg = sys.argv[1].strip()
    if arg in ("--version", "-v"):
        print(f"hitesh-fastapi-starter version {__version__}")
        sys.exit(0)

    if arg in ("--help", "-h"):
        print_banner()
        print("Usage: fastapi-starter <project_name>\n")
        print("Arguments:")
        print("  <project_name>   Name of the directory and project to scaffold\n")
        print("Options:")
        print("  -v, --version    Show version number")
        print("  -h, --help       Show this help message")
        sys.exit(0)

    create_project(arg)


def create_project(project_name: str):
    print_banner()
    base = os.path.abspath(project_name)

    if os.path.exists(base) and os.listdir(base):
        print(f"⚠️  Directory '{project_name}' already exists and is not empty.")
        proceed = input("Do you want to continue and overwrite files? [y/N]: ").strip().lower()
        if proceed not in ("y", "yes"):
            print("Operation aborted.")
            sys.exit(1)

    print(f"📁 Scaffolding FastAPI project into: {base}\n")

    templates = get_all_templates(project_name)
    total_files = len(templates)
    created_count = 0

    for rel_path, content in templates.items():
        file_path = os.path.join(base, rel_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        created_count += 1
        print(f"  ✓ Created: {rel_path}")

    # Create empty directories needed for runtime
    os.makedirs(os.path.join(base, "logs"), exist_ok=True)
    os.makedirs(os.path.join(base, "redis-data"), exist_ok=True)

    print(f"\n🎉 Successfully created {created_count} files for '{project_name}'!")
    print("\nNext Steps:")
    print(f"  1. Navigate to the project:")
    print(f"     cd {project_name}")
    print(f"  2. Create virtual environment and install dependencies:")
    print(f"     python -m venv venv")
    print(f"     source venv/bin/activate   # On Windows: venv\\Scripts\\activate")
    print(f"     pip install -r requirement.txt")
    print(f"  3. Configure environment:")
    print(f"     cp .env.example .env")
    print(f"  4. Start all microservices + API Gateway:")
    print(f"     python run_internal_services.py")
    print(f"\n👉 Swagger API Docs will be available at: http://127.0.0.1:7060/docs")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    create_project_cli()
