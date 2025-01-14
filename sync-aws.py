import re
import os
import platform
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import Playwright, sync_playwright

def set_aws_credentials_system_wide(file_path=".aws-credentials"):
    """
    Carga las credenciales de AWS desde un archivo y las establece como variables de entorno.
    """
    file = Path(file_path)
    if not file.is_file():
        print(f"Error: El archivo {file_path} no se encuentra.")
        return

    try:
        with open(file, "r") as f:
            for line in f:
                match = re.match(r'^(aws_access_key|aws_secret_key|aws_session_token)="(.*)"$', line)
                if match:
                    variable_name, value = match.groups()
                    variable_name = variable_name.upper()
                    if platform.system() == 'Windows':
                        set_windows_env_variable(variable_name, value)
                    else:
                        os.environ[variable_name] = value
                        print(f"Variable '{variable_name}' establecida.")
    except Exception as e:
        print(f"Error al procesar el archivo: {e}")

def set_windows_env_variable(variable_name, value):
    """Establece una variable de entorno en Windows."""
    try:
        subprocess.run(["setx", variable_name, value], check=True, capture_output=True, text=True)
        print(f"Variable de entorno de usuario '{variable_name}' establecida.")
    except subprocess.CalledProcessError:
        print(f"Intentando establecer la variable '{variable_name}' a nivel del sistema.")
        try:
            subprocess.run(["setx", variable_name, value, "/M"], check=True, capture_output=True, text=True)
            print(f"Variable de entorno de sistema '{variable_name}' establecida.")
        except subprocess.CalledProcessError as e:
            print(f"Error al establecer la variable '{variable_name}': {e}")

def run(playwright: Playwright):
    """Automatiza la navegación para sincronizar credenciales de AWS."""
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)

    load_dotenv(dotenv_path=script_dir / ".env")
    email, password = os.getenv("MICROSOFT_EMAIL"), os.getenv("MICROSOFT_PASSWORD")

    if not email or not password:
        print("Error: MICROSOFT_EMAIL y/o MICROSOFT_PASSWORD no están definidas en el archivo .env.")
        return

    state_path = script_dir / "playwright_state.json"
    browser = playwright.chromium.launch(headless=True)
    context = (browser.new_context(storage_state=state_path)
               if state_path.exists() else browser.new_context())

    page = context.new_page()
    page.goto("https://d-8067060d87.awsapps.com/start/#/?tab=accounts")

    handle_cookies_modal(page)

    if not validate_session(page):
        perform_login(page, email, password, state_path)

    navigate_to_credentials(page)
    credentials = extract_credentials(page)

    if credentials:
        save_credentials(credentials)
        set_aws_credentials_system_wide(".aws-credentials")

    context.close()
    browser.close()

def handle_cookies_modal(page):
    """Maneja el modal de cookies si aparece."""
    try:
        page.locator("[data-id='awsccc-cb-btn-accept']").click(timeout=5000)
        print("Cookies aceptadas.")
    except:
        print("No se mostró el modal de cookies.")

def validate_session(page):
    """Valida si la sesión es válida."""
    try:
        page.wait_for_selector("[data-testid='account-list-cell']", timeout=15000)
        print("Sesión válida.")
        return True
    except:
        print("Sesión no válida. Requiere inicio de sesión.")
        return False

def perform_login(page, email, password, state_path):
    """Realiza el inicio de sesión en Microsoft."""
    page.get_by_placeholder("Correo electrónico, teléfono").fill(email)
    page.get_by_role("button", name="Siguiente").click()
    page.get_by_placeholder("Contraseña").fill(password)
    page.get_by_role("button", name="Iniciar sesión").click()

    try:
        page.get_by_text("No volver a mostrar").click()
    except:
        pass

    page.get_by_role("button", name="Sí").click()
    context = page.context
    context.storage_state(path=str(state_path))
    print("Sesión guardada.")

def navigate_to_credentials(page):
    """Navega hasta la sección de credenciales."""
    try:
        page.locator("[data-testid='account-list-cell']").click()
        page.locator("[data-testid='role-creation-action-button']").click()
        page.wait_for_selector("text=export AWS_ACCESS_KEY_ID", timeout=30000)
        print("Navegación a credenciales completada.")
    except Exception as e:
        print(f"Error al navegar a las credenciales: {e}")
        raise

def extract_credentials(page):
    """Extrae las credenciales de AWS de la página."""
    try:
        credentials = {}
        for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]:
            selector = f"text=export {key}"
            element_text = page.locator(selector).inner_text()
            match = re.search(fr'export {key}="([^"]+)"', element_text)
            credentials[key.lower()] = match.group(1) if match else ""
        print("Credenciales extraídas.")
        return credentials
    except Exception as e:
        print(f"Error al extraer credenciales: {e}")
        return None

def convert_linux_to_windows_path(linux_path):
    """
    Convierte una ruta de Linux (WSL) a una ruta de Windows accesible.
    """
    try:
        windows_path = subprocess.check_output(["wslpath", "-w", linux_path], text=True).strip()
        return windows_path
    except Exception as e:
        print(f"Error al convertir la ruta de Linux a Windows: {e}")
        return None

def save_credentials(credentials, file_path=".aws-credentials", wsl_linux_path="/home/bootcamp/.aws/credentials"):
    """
    Guarda las credenciales en archivos específicos y conserva el perfil existente.
    """
    try:
        # Guardar en el archivo local .aws-credentials
        with open(file_path, "w") as f:
            for key, value in credentials.items():
                f.write(f'{key}={value}\n')
        print(f"Credenciales guardadas en {file_path}.")

        # Construir la ruta de Windows manualmente a partir de la ruta de WSL
        wsl_windows_path = wsl_linux_path.replace("/", "\\")
        wsl_windows_path = f"\\\\wsl.localhost\\Debian{wsl_windows_path}"

        if os.path.exists(wsl_windows_path):
            # Modificar el archivo en WSL
            with open(wsl_windows_path, "r") as f:
                lines = f.readlines()

            with open(wsl_windows_path, "w") as f:
                in_profile_section = False
                for line in lines:
                    if line.strip() == "[DiegoPerez-Profile]":
                        in_profile_section = True
                        f.write(line)
                        continue

                    if in_profile_section:
                        if line.startswith("aws_access_key_id"):
                            f.write(f'aws_access_key_id={credentials["aws_access_key_id"]}\n')
                        elif line.startswith("aws_secret_access_key"):
                            f.write(f'aws_secret_access_key={credentials["aws_secret_access_key"]}\n')
                        elif line.startswith("aws_session_token"):
                            f.write(f'aws_session_token={credentials["aws_session_token"]}\n')
                        else:
                            f.write(line)
                    else:
                        f.write(line)

            print(f"Credenciales actualizadas en {wsl_windows_path}.")
        else:
            print(f"La ruta {wsl_windows_path} no existe o no es accesible.")
    except Exception as e:
        print(f"Error al guardar las credenciales: {e}")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
