#!/usr/bin/env python3

import asyncio
import argparse
from glob import glob
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import sysconfig
from asyncio import wait_for
from contextlib import asynccontextmanager
from os.path import basename, relpath
from pathlib import Path
from subprocess import CalledProcessError
from tempfile import TemporaryDirectory


SCRIPT_NAME = Path(__file__).name
CHECKOUT = Path(__file__).resolve().parent.parent
ANDROID_DIR = CHECKOUT / "Android"
TESTBED_DIR = ANDROID_DIR / "testbed"
CROSS_BUILD_DIR = CHECKOUT / "cross-build"

APP_ID = "org.python.testbed"
DECODE_ARGS = ("UTF-8", "backslashreplace")


try:
    android_home = Path(os.environ['ANDROID_HOME'])
except KeyError:
    sys.exit("The ANDROID_HOME environment variable is required.")

adb = Path(
    f"{android_home}/platform-tools/adb"
    + (".exe" if os.name == "nt" else "")
)

gradlew = Path(
    f"{TESTBED_DIR}/gradlew"
    + (".bat" if os.name == "nt" else "")
)

logcat_started = False


def delete_glob(pattern):
    # Path.glob doesn't accept non-relative patterns.
    for path in glob(str(pattern)):
        path = Path(path)
        print(f"Deleting {path} ...")
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()


def subdir(name, *, clean=None):
    path = CROSS_BUILD_DIR / name
    if clean:
        delete_glob(path)
    if not path.exists():
        if clean is None:
            sys.exit(
                f"{path} does not exist. Create it by running the appropriate "
                f"`configure` subcommand of {SCRIPT_NAME}.")
        else:
            path.mkdir(parents=True)
    return path


def run(command, *, host=None, env=None, log=True, **kwargs):
    kwargs.setdefault("check", True)
    if env is None:
        env = os.environ.copy()
    original_env = env.copy()

    if host:
        env_script = ANDROID_DIR / "android-env.sh"
        env_output = subprocess.run(
            f"set -eu; "
            f"HOST={host}; "
            f"PREFIX={subdir(host)}/prefix; "
            f". {env_script}; "
            f"export",
            check=True, shell=True, text=True, stdout=subprocess.PIPE
        ).stdout

        for line in env_output.splitlines():
            # We don't require every line to match, as there may be some other
            # output from installing the NDK.
            if match := re.search(
                "^(declare -x |export )?(\\w+)=['\"]?(.*?)['\"]?$", line
            ):
                key, value = match[2], match[3]
                if env.get(key) != value:
                    print(line)
                    env[key] = value

        if env == original_env:
            raise ValueError(f"Found no variables in {env_script.name} output:\n"
                             + env_output)

    if log:
        print(">", " ".join(map(str, command)))
    return subprocess.run(command, env=env, **kwargs)


def build_python_path():
    """The path to the build Python binary."""
    build_dir = subdir("build")
    binary = build_dir / "python"
    if not binary.is_file():
        binary = binary.with_suffix(".exe")
        if not binary.is_file():
            raise FileNotFoundError("Unable to find `python(.exe)` in "
                                    f"{build_dir}")

    return binary


def configure_build_python(context):
    os.chdir(subdir("build", clean=context.clean))

    command = [relpath(CHECKOUT / "configure")]
    if context.args:
        command.extend(context.args)
    run(command)


def make_build_python(context):
    os.chdir(subdir("build"))
    run(["make", "-j", str(os.cpu_count())])


def unpack_deps(host):
    deps_url = "https://github.com/beeware/cpython-android-source-deps/releases/download"
    for name_ver in ["bzip2-1.0.8-2", "libffi-3.4.4-3", "openssl-3.0.15-4",
                     "sqlite-3.45.3-3", "xz-5.4.6-1"]:
        filename = f"{name_ver}-{host}.tar.gz"
        download(f"{deps_url}/{name_ver}/{filename}")
        run(["tar", "-xf", filename])
        os.remove(filename)


def download(url, target_dir="."):
    out_path = f"{target_dir}/{basename(url)}"
    run(["curl", "-Lf", "-o", out_path, url])
    return out_path


def configure_host_python(context):
    host_dir = subdir(context.host, clean=context.clean)

    prefix_dir = host_dir / "prefix"
    if not prefix_dir.exists():
        prefix_dir.mkdir()
        os.chdir(prefix_dir)
        unpack_deps(context.host)

    build_dir = host_dir / "build"
    build_dir.mkdir(exist_ok=True)
    os.chdir(build_dir)

    command = [
        # Basic cross-compiling configuration
        relpath(CHECKOUT / "configure"),
        f"--host={context.host}",
        f"--build={sysconfig.get_config_var('BUILD_GNU_TYPE')}",
        f"--with-build-python={build_python_path()}",
        "--without-ensurepip",

        # Android always uses a shared libpython.
        "--enable-shared",
        "--without-static-libpython",

        # Dependent libraries. The others are found using pkg-config: see
        # android-env.sh.
        f"--with-openssl={prefix_dir}",
    ]

    if context.args:
        command.extend(context.args)
    run(command, host=context.host)


def make_host_python(context):
    # The CFLAGS and LDFLAGS set in android-env include the prefix dir, so
    # delete any previous Python installation to prevent it being used during
    # the build.
    host_dir = subdir(context.host)
    prefix_dir = host_dir / "prefix"
    delete_glob(f"{prefix_dir}/include/python*")
    delete_glob(f"{prefix_dir}/lib/libpython*")
    delete_glob(f"{prefix_dir}/lib/python*")

    os.chdir(host_dir / "build")
    run(["make", "-j", str(os.cpu_count())], host=context.host)
    run(["make", "install", f"prefix={prefix_dir}"], host=context.host)


def build_all(context):
    steps = [configure_build_python, make_build_python, configure_host_python,
             make_host_python]
    for step in steps:
        step(context)


def clean_all(context):
    delete_glob(CROSS_BUILD_DIR)


def setup_sdk():
    sdkmanager = android_home / (
        "cmdline-tools/latest/bin/sdkmanager"
        + (".bat" if os.name == "nt" else "")
    )

    # Gradle will fail if it needs to install an SDK package whose license
    # hasn't been accepted, so pre-accept all licenses.
    if not all((android_home / "licenses" / path).exists() for path in [
        "android-sdk-arm-dbt-license", "android-sdk-license"
    ]):
        run([sdkmanager, "--licenses"], text=True, input="y\n" * 100)

    # Gradle may install this automatically, but we can't rely on that because
    # we need to run adb within the logcat task.
    if not adb.exists():
        run([sdkmanager, "platform-tools"])


# To avoid distributing compiled artifacts without corresponding source code,
# the Gradle wrapper is not included in the CPython repository. Instead, we
# extract it from the Gradle release.
def setup_testbed():
    if all((TESTBED_DIR / path).exists() for path in [
        "gradlew", "gradlew.bat", "gradle/wrapper/gradle-wrapper.jar",
    ]):
        return

    ver_long = "8.7.0"
    ver_short = ver_long.removesuffix(".0")

    for filename in ["gradlew", "gradlew.bat"]:
        out_path = download(
            f"https://raw.githubusercontent.com/gradle/gradle/v{ver_long}/{filename}",
            TESTBED_DIR)
        os.chmod(out_path, 0o755)

    with TemporaryDirectory(prefix=SCRIPT_NAME) as temp_dir:
        bin_zip = download(
            f"https://services.gradle.org/distributions/gradle-{ver_short}-bin.zip",
            temp_dir)
        outer_jar = f"gradle-{ver_short}/lib/plugins/gradle-wrapper-{ver_short}.jar"
        run(["unzip", "-d", temp_dir, bin_zip, outer_jar])
        run(["unzip", "-o", "-d", f"{TESTBED_DIR}/gradle/wrapper",
             f"{temp_dir}/{outer_jar}", "gradle-wrapper.jar"])


# run_testbed will build the app automatically, but it's useful to have this as
# a separate command to allow running the app outside of this script.
def build_testbed(context):
    setup_sdk()
    setup_testbed()
    run(
        [gradlew, "--console", "plain", "packageDebug", "packageDebugAndroidTest"],
        cwd=TESTBED_DIR,
    )


# Work around a bug involving sys.exit and TaskGroups
# (https://github.com/python/cpython/issues/101515).
def exit(*args):
    raise MySystemExit(*args)


class MySystemExit(Exception):
    pass


# The `test` subcommand runs all subprocesses through this context manager so
# that no matter what happens, they can always be cancelled from another task,
# and they will always be cleaned up on exit.
@asynccontextmanager
async def async_process(*args, **kwargs):
    process = await asyncio.create_subprocess_exec(*args, **kwargs)
    try:
        yield process
    finally:
        if process.returncode is None:
            # Allow a reasonably long time for Gradle to clean itself up,
            # because we don't want stale emulators left behind.
            timeout = 10
            process.terminate()
            try:
                await wait_for(process.wait(), timeout)
            except TimeoutError:
                print(
                    f"Command {args} did not terminate after {timeout} seconds "
                    f" - sending SIGKILL"
                )
                process.kill()

                # Even after killing the process we must still wait for it,
                # otherwise we'll get the warning "Exception ignored in __del__".
                await wait_for(process.wait(), timeout=1)


async def async_check_output(*args, **kwargs):
    async with async_process(
        *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs
    ) as process:
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return stdout.decode(*DECODE_ARGS)
        else:
            raise CalledProcessError(
                process.returncode, args,
                stdout.decode(*DECODE_ARGS), stderr.decode(*DECODE_ARGS)
            )


# Return a list of the serial numbers of connected devices. Emulators will have
# serials of the form "emulator-5678".
async def list_devices():
    serials = []
    header_found = False

    lines = (await async_check_output(adb, "devices")).splitlines()
    for line in lines:
        # Ignore blank lines, and all lines before the header.
        line = line.strip()
        if line == "List of devices attached":
            header_found = True
        elif header_found and line:
            try:
                serial, status = line.split()
            except ValueError:
                raise ValueError(f"failed to parse {line!r}")
            if status == "device":
                serials.append(serial)

    if not header_found:
        raise ValueError(f"failed to parse {lines}")
    return serials


async def find_device(context, initial_devices):
    if context.managed:
        print("Waiting for managed device - this may take several minutes")
        while True:
            new_devices = set(await list_devices()).difference(initial_devices)
            if len(new_devices) == 0:
                await asyncio.sleep(1)
            elif len(new_devices) == 1:
                serial = new_devices.pop()
                print(f"Serial: {serial}")
                return serial
            else:
                exit(f"Found more than one new device: {new_devices}")
    else:
        return context.connected


# An older version of this script in #121595 filtered the logs by UID instead.
# But logcat can't filter by UID until API level 31. If we ever switch back to
# filtering by UID, we'll also have to filter by time so we only show messages
# produced after the initial call to `stop_app`.
#
# We're more likely to miss the PID because it's shorter-lived, so there's a
# workaround in PythonSuite.kt to stop it being *too* short-lived.
async def find_pid(serial):
    print("Waiting for app to start - this may take several minutes")
    shown_error = False
    while True:
        try:
            # `pidof` requires API level 24 or higher. The level 23 emulator
            # includes it, but it doesn't work (it returns all processes).
            pid = (await async_check_output(
                adb, "-s", serial, "shell", "pidof", "-s", APP_ID
            )).strip()
        except CalledProcessError as e:
            # If the app isn't running yet, pidof gives no output. So if there
            # is output, there must have been some other error. However, this
            # sometimes happens transiently, especially when running a managed
            # emulator for the first time, so don't make it fatal.
            if (e.stdout or e.stderr) and not shown_error:
                print_called_process_error(e)
                print("This may be transient, so continuing to wait")
                shown_error = True
        else:
            # Some older devices (e.g. Nexus 4) return zero even when no process
            # was found, so check whether we actually got any output.
            if pid:
                print(f"PID: {pid}")
                return pid

        # Loop fairly rapidly to avoid missing a short-lived process.
        await asyncio.sleep(0.2)


async def logcat_task(context, initial_devices):
    # Gradle may need to do some large downloads of libraries and emulator
    # images. This will happen during find_device in --managed mode, or find_pid
    # in --connected mode.
    startup_timeout = 600
    serial = await wait_for(find_device(context, initial_devices), startup_timeout)
    pid = await wait_for(find_pid(serial), startup_timeout)

    # `--pid` requires API level 24 or higher.
    args = [adb, "-s", serial, "logcat", "--pid", pid,  "--format", "tag"]
    hidden_output = []
    async with async_process(
        *args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    ) as process:
        while line := (await process.stdout.readline()).decode(*DECODE_ARGS):
            if match := re.fullmatch(r"([A-Z])/(.*)", line, re.DOTALL):
                level, message = match.groups()
            else:
                # If the regex doesn't match, this is probably the second or
                # subsequent line of a multi-line message. Python won't produce
                # such messages, but other components might.
                level, message = None, line

            # Exclude high-volume messages which are rarely useful.
            if context.verbose < 2 and "from python test_syslog" in message:
                continue

            # Put high-level messages on stderr so they're highlighted in the
            # buildbot logs. This will include Python's own stderr.
            stream = (
                sys.stderr
                if level in ["W", "E", "F"]  # WARNING, ERROR, FATAL (aka ASSERT)
                else sys.stdout
            )

            # To simplify automated processing of the output, e.g. a buildbot
            # posting a failure notice on a GitHub PR, we strip the level and
            # tag indicators from Python's stdout and stderr.
            for prefix in ["python.stdout: ", "python.stderr: "]:
                if message.startswith(prefix):
                    global logcat_started
                    logcat_started = True
                    stream.write(message.removeprefix(prefix))
                    break
            else:
                if context.verbose:
                    # Non-Python messages add a lot of noise, but they may
                    # sometimes help explain a failure.
                    stream.write(line)
                else:
                    hidden_output.append(line)

        # If the device disconnects while logcat is running, which always
        # happens in --managed mode, some versions of adb return non-zero.
        # Distinguish this from a logcat startup error by checking whether we've
        # received a message from Python yet.
        status = await wait_for(process.wait(), timeout=1)
        if status != 0 and not logcat_started:
            raise CalledProcessError(status, args, "".join(hidden_output))


def stop_app(serial):
    run([adb, "-s", serial, "shell", "am", "force-stop", APP_ID], log=False)


async def gradle_task(context):
    env = os.environ.copy()
    if context.managed:
        task_prefix = context.managed
    else:
        task_prefix = "connected"
        env["ANDROID_SERIAL"] = context.connected

    args = [
        gradlew, "--console", "plain", f"{task_prefix}DebugAndroidTest",
        "-Pandroid.testInstrumentationRunnerArguments.pythonArgs="
        + shlex.join(context.args),
    ]
    hidden_output = []
    try:
        async with async_process(
            *args, cwd=TESTBED_DIR, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        ) as process:
            while line := (await process.stdout.readline()).decode(*DECODE_ARGS):
                # Gradle may take several minutes to install SDK packages, so
                # it's worth showing those messages even in non-verbose mode.
                if context.verbose or line.startswith('Preparing "Install'):
                    sys.stdout.write(line)
                else:
                    hidden_output.append(line)

            status = await wait_for(process.wait(), timeout=1)
            if status == 0:
                exit(0)
            else:
                raise CalledProcessError(status, args)
    finally:
        # If logcat never started, then something has gone badly wrong, so the
        # user probably wants to see the Gradle output even in non-verbose mode.
        if hidden_output and not logcat_started:
            sys.stdout.write("".join(hidden_output))

        # Gradle does not stop the tests when interrupted.
        if context.connected:
            stop_app(context.connected)


async def run_testbed(context):
    setup_sdk()
    setup_testbed()

    if context.managed:
        # In this mode, Gradle will create a device with an unpredictable name.
        # So we save a list of the running devices before starting Gradle, and
        # find_device then waits for a new device to appear.
        initial_devices = await list_devices()
    else:
        # In case the previous shutdown was unclean, make sure the app isn't
        # running, otherwise we might show logs from a previous run. This is
        # unnecessary in --managed mode, because Gradle creates a new emulator
        # every time.
        stop_app(context.connected)
        initial_devices = None

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(logcat_task(context, initial_devices))
            tg.create_task(gradle_task(context))
    except* MySystemExit as e:
        raise SystemExit(*e.exceptions[0].args) from None
    except* CalledProcessError as e:
        # Extract it from the ExceptionGroup so it can be handled by `main`.
        raise e.exceptions[0]


# Handle SIGTERM the same way as SIGINT. This ensures that if we're terminated
# by the buildbot worker, we'll make an attempt to clean up our subprocesses.
def install_signal_handler():
    def signal_handler(*args):
        os.kill(os.getpid(), signal.SIGINT)

    signal.signal(signal.SIGTERM, signal_handler)


def parse_args():
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="subcommand")
    build = subcommands.add_parser("build", help="Build everything")
    configure_build = subcommands.add_parser("configure-build",
                                             help="Run `configure` for the "
                                             "build Python")
    make_build = subcommands.add_parser("make-build",
                                        help="Run `make` for the build Python")
    configure_host = subcommands.add_parser("configure-host",
                                            help="Run `configure` for Android")
    make_host = subcommands.add_parser("make-host",
                                       help="Run `make` for Android")
    subcommands.add_parser(
        "clean", help="Delete the cross-build directory")

    for subcommand in build, configure_build, configure_host:
        subcommand.add_argument(
            "--clean", action="store_true", default=False, dest="clean",
            help="Delete any relevant directories before building")
    for subcommand in build, configure_host, make_host:
        subcommand.add_argument(
            "host", metavar="HOST",
            choices=["aarch64-linux-android", "x86_64-linux-android"],
            help="Host triplet: choices=[%(choices)s]")
    for subcommand in build, configure_build, configure_host:
        subcommand.add_argument("args", nargs="*",
                                help="Extra arguments to pass to `configure`")

    subcommands.add_parser(
        "build-testbed", help="Build the testbed app")
    test = subcommands.add_parser(
        "test", help="Run the test suite")
    test.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Show Gradle output, and non-Python logcat messages. "
        "Use twice to include high-volume messages which are rarely useful.")
    device_group = test.add_mutually_exclusive_group(required=True)
    device_group.add_argument(
        "--connected", metavar="SERIAL", help="Run on a connected device. "
        "Connect it yourself, then get its serial from `adb devices`.")
    device_group.add_argument(
        "--managed", metavar="NAME", help="Run on a Gradle-managed device. "
        "These are defined in `managedDevices` in testbed/app/build.gradle.kts.")
    test.add_argument(
        "args", nargs="*", help=f"Arguments for `python -m test`. "
        f"Separate them from {SCRIPT_NAME}'s own arguments with `--`.")

    return parser.parse_args()


def main():
    install_signal_handler()

    # Under the buildbot, stdout is not a TTY, but we must still flush after
    # every line to make sure our output appears in the correct order relative
    # to the output of our subprocesses.
    for stream in [sys.stdout, sys.stderr]:
        stream.reconfigure(line_buffering=True)

    context = parse_args()
    dispatch = {"configure-build": configure_build_python,
                "make-build": make_build_python,
                "configure-host": configure_host_python,
                "make-host": make_host_python,
                "build": build_all,
                "clean": clean_all,
                "build-testbed": build_testbed,
                "test": run_testbed}

    try:
        result = dispatch[context.subcommand](context)
        if asyncio.iscoroutine(result):
            asyncio.run(result)
    except CalledProcessError as e:
        print_called_process_error(e)
        sys.exit(1)


def print_called_process_error(e):
    for stream_name in ["stdout", "stderr"]:
        content = getattr(e, stream_name)
        stream = getattr(sys, stream_name)
        if content:
            stream.write(content)
            if not content.endswith("\n"):
                stream.write("\n")

    # Format the command so it can be copied into a shell. shlex uses single
    # quotes, so we surround the whole command with double quotes.
    args_joined = (
        e.cmd if isinstance(e.cmd, str)
        else " ".join(shlex.quote(str(arg)) for arg in e.cmd)
    )
    print(
        f'Command "{args_joined}" returned exit status {e.returncode}'
    )


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""
PROYECTO ALVAREZTRUCKING1 - INTEGRADO EN REPOSITORIO CPython
Descripción: Script para gestión de redes sociales y datos empresariales
Autor: [Tu nombre]
Fecha: 2026-01-07
Versión: 1.2
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional

# Rutas relativas dentro del repositorio CPython
RUTA_CONFIG = os.path.join(os.path.dirname(__file__), "config", "configuracion.json")
RUTA_DATOS = os.path.join(os.path.dirname(__file__), "datos")

# Crear carpeta de datos si no existe
os.makedirs(RUTA_DATOS, exist_ok=True)


# -------------------------- CLASE: CARGA DE CONFIGURACIÓN --------------------------
class CargadorConfiguracion:
    """Carga datos fijos de la empresa desde archivo JSON"""
    @staticmethod
    def cargar() -> Dict:
        try:
            with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise Exception(f"Archivo de configuración no encontrado en {RUTA_CONFIG}")


# -------------------------- CLASE: ANALIZADOR DE PERFILES --------------------------
class AnalizadorRedesSociales:
    """Analiza y almacena datos de perfiles empresariales"""
    def __init__(self):
        self.config = CargadorConfiguracion.cargar()
        self.nombre_principal = self.config["nombre_empresa"]
        self.datos_perfiles: Dict[str, Dict] = {}
        self.datos_empresa: Dict = {}

    def cargar_datos_perfil(self, plataforma: str, seguidores: int, siguiendo: int, me_gusta: int):
        """Carga datos de perfiles con descripción desde configuración"""
        plataforma = plataforma.lower()
        descripcion = (
            f"{self.nombre_principal} - {self.config['rubro']} en {self.config['direccion']} 🚚 | "
            f"{self.config['servicios']} | Contáctanos: {self.config['contacto']['telefono']}"
        )

        self.datos_perfiles[plataforma] = {
            "nombre_usuario": self.config["redes_sociales"][plataforma],
            "seguidores": seguidores,
            "siguiendo": siguiendo,
            "me_gusta_totales": me_gusta,
            "descripcion": descripcion,
            "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "hashtags_destacados": self._obtener_hashtags(plataforma)
        }

    def cargar_datos_empresa(self):
        """Carga datos empresariales desde configuración"""
        self.datos_empresa = {
            "nombre": self.nombre_principal,
            "rubro": self.config["rubro"],
            "direccion": self.config["direccion"],
            "servicios": self.config["servicios"],
            "contacto": self.config["contacto"],
            "horario_atencion": "Lunes a Viernes: 08:00 - 18:00 | Sábados: 09:00 - 14:00"
        }

    def _obtener_hashtags(self, plataforma: str) -> list:
        """Hashtags personalizados por plataforma"""
        hashtags_base = ["#AlvarezTrucking1", "#Transporte", "#Logistica", "#Saltillo", "#Coahuila"]
        plataforma_hashtags = {
            "kwai": ["#KwaiEmpresarial", "#TransporteMexicano"],
            "instagram": ["#InstagramEmpresarial", "#LogisticaMexicana"],
            "tiktok": ["#TikTokNegocios", "#Camiones"],
            "facebook": ["#FacebookEmpresarial", "#EmpresaMexicana"]
        }
        return hashtags_base + plataforma_hashtags.get(plataforma, [])

    def generar_resumen_completo(self) -> str:
        """Genera reportes en la carpeta datos/"""
        resumen_texto = f"=== RESUMEN ALVAREZTRUCKING1 - REDES SOCIALES ===\n"
        resumen_texto += f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

        # Datos de la empresa
        resumen_texto += "--- DATOS EMPRESARIALES ---\n"
        resumen_texto += f"Nombre: {self.datos_empresa['nombre']}\n"
        resumen_texto += f"Rubro: {self.datos_empresa['rubro']}\n"
        resumen_texto += f"Contacto: {self.datos_empresa['contacto']['telefono']} | {self.datos_empresa['contacto']['correo']}\n\n"

        # Datos de perfiles
        resumen_texto += "--- PERFILES POR PLATAFORMA ---\n"
        for plataforma, datos in self.datos_perfiles.items():
            resumen_texto += f"\n> {plataforma.upper()}\n"
            resumen_texto += f"  Usuario: {datos['nombre_usuario']}\n"
            resumen_texto += f"  Seguidores: {datos['seguidores']}\n"
            resumen_texto += f"  Hashtags: {' '.join(datos['hashtags_destacados'])}\n"

        # Guardar archivos
        nombre_archivo = f"resumen_{self.nombre_principal}_{datetime.now().strftime('%Y%m%d')}"
        with open(os.path.join(RUTA_DATOS, f"{nombre_archivo}.txt"), "w", encoding="utf-8") as f_txt:
            f_txt.write(resumen_texto)
        
        with open(os.path.join(RUTA_DATOS, f"{nombre_archivo}.json"), "w", encoding="utf-8") as f_json:
            json.dump({
                "empresa": self.datos_empresa,
                "perfiles": self.datos_perfiles
            }, f_json, indent=2, ensure_ascii=False)

        return resumen_texto


# -------------------------- CLASE: GENERADOR DE PUBLICACIONES --------------------------
class GeneradorPublicaciones:
    """Genera plantillas adaptadas a la empresa"""
    def __init__(self):
        self.config = CargadorConfiguracion.cargar()
        self.plantillas: Dict[str, Dict] = {
            "kwai": {
                "servicio": "📦 Ofrecemos {servicio} en {ubicacion}!\nContáctanos: {telefono}\n{hashtags}",
                "novedad": "🚚 ¡Nueva unidad en nuestra flota! 🎉\nMás capacidad para tu mercancía\n{hashtags}",
                "testimonio": "🙌 Cliente {cliente}: {comentario}\nGracias por confiar en nosotros!\n{hashtags}"
            },
            "instagram": {
                "foto_flota": "📸 Conoce nuestra flota de camiones\n{descripcion}\n{hashtags}\n📞 {telefono}",
                "oferta": "📢 OFERTA ESPECIAL! Descuento en envíos a {destino}\nValido hasta {fecha_limite}\n{hashtags}",
                "reel": "¿Cómo gestionamos tus envíos? 🎬 Mira nuestro proceso\n{hashtags}"
            },
            "tiktok": {
                "flota": "Conoce nuestras unidades 🚚💨\n{contenido}\n{hashtags}",
                "tutorial": "¿Cómo preparar tu mercancía? 📦\n{contenido}\n{hashtags}",
                "evento": "¡Estuvimos en {evento}! 🤝 Conociendo aliados\n{hashtags}"
            },
            "facebook": {
                "publicacion": "✅ {servicio} confiable en {ubicacion}\n{descripcion}\nCotiza aquí: {correo}\n{hashtags}",
                "evento": "📅 ¡Feria de Logística de Saltillo! 📍 Stand {stand}\nFecha: {fecha}\nVisítanos!\n{hashtags}",
                "aviso": "⚠️ Aviso: Horarios especiales en {periodo}\n{informacion}\n{hashtags}"
            }
        }

    def crear_publicacion(self, plataforma: str, tipo: str, **kwargs) -> str:
        """Genera publicación con datos de la empresa"""
        plataforma = plataforma.lower()
        if plataforma not in self.plantillas or tipo not in self.plantillas[plataforma]:
            return "[ERROR] Tipo o plataforma no válidos"

        # Agregar datos de la empresa si no se proporcionan
        kwargs.setdefault("telefono", self.config["contacto"]["telefono"])
        kwargs.setdefault("correo", self.config["contacto"]["correo"])
        kwargs.setdefault("hashtags", " ".join([
            "#AlvarezTrucking1", "#Transporte", "#Logistica", f"#{plataforma.capitalize()}"
        ]))

        return self.plantillas[plataforma][tipo].format(**kwargs)


# -------------------------- EJECUCIÓN PRINCIPAL --------------------------
if __name__ == "__main__":
    print("=== INICIANDO GESTIÓN ALVAREZTRUCKING1 ===")

    # 1. Cargar y analizar datos
    analizador = AnalizadorRedesSociales()
    analizador.cargar_datos_empresa()
    
    # Cargar métricas de redes sociales
    analizador.cargar_datos_perfil("Kwai", 2800, 150, 12500)
    analizador.cargar_datos_perfil("Instagram", 5400, 320, 38200)
    analizador.cargar_datos_perfil("TikTok", 3900, 210, 26700)
    analizador.cargar_datos_perfil("Facebook", 4200, 180, 23100)

    # Generar resumen
    print("\n--- RESUMEN GENERADO ---")
    print(analizador.generar_resumen_completo())
    print(f"\nReportes guardados en: {RUTA_DATOS}")

    # 2. Generar ejemplos de publicaciones
    generador = GeneradorPublicaciones()
    print("\n--- EJEMPLOS DE PUBLICACIONES ---")
    
    pub_insta = generador.crear_publicacion(
        plataforma="Instagram",
        tipo="foto_flota",
        descripcion="Unidades equipadas con tecnología de seguimiento GPS para mayor seguridad",
        hashtags="#AlvarezTrucking1 #Transporte #Logistica #Saltillo #FlotaModerna"
    )
    print("> INSTAGRAM:\n", pub_insta, "\n")

    pub_tiktok = generador.crear_publicacion(
        plataforma="TikTok",
        tipo="tutorial",
        contenido="Empaqueta tu mercancía con materiales resistentes y etiqueta claramente el destino",
        hashtags="#AlvarezTrucking1 #TikTok #Logistica #Consejos #Transporte"
    )
    print("> TIKTOK:\n", pub_tiktok)

    print("\n=== PROCESO COMPLETADO ===")
