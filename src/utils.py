import os
import apt
import subprocess
import tarfile
from jinja2 import Template
import shutil
import netifaces as ni


def get_command_output(command: str) -> str:
    stream = os.popen(command)
    output = stream.read()
    return output.strip()


def execute_script(executer: str, script, *args) -> None:
    call_list = [executer, script]
    if args:
        for arg in args:
            call_list.append(arg)
    subprocess.call(call_list)


def get_interface_ip(ens_name: str) -> str:
    ni.ifaddresses(ens_name)
    ip = ni.ifaddresses(ens_name)[ni.AF_INET][0]["addr"]
    return ip.strip()


def append_line_tofile(*args: str, filename: str) -> None:
    with open(filename, "a", encoding="utf-8") as target_file:
        concataneted_line = ""
        for arg in args:
            concataneted_line += arg.strip() + " "
        target_file.write(concataneted_line + "\n")


def append_tofile(*args: str, filename: str) -> None:
    with open(filename, "a", encoding="utf-8") as target_file:
        for arg in args:
            target_file.write(arg + "\n")


def install_packages(packages: list, update: bool = False, progress=None) -> None:
    cache = apt.cache.Cache()
    if update:
        cache.update()
    cache.open()
    for package in packages:
        pkg = cache[package]
        print(pkg)
        if not pkg.is_installed:
            pkg.mark_install()
            cache.commit(install_progress=progress)


def install_local_packages(packages: list) -> None:
    subprocess.run(
        ["apt-get", "-y", "--allow-unauthenticated", "install", *packages]
    ).check_returncode()


def shell(command: str) -> None:
    subprocess.run(command, shell=True).check_returncode()


def _systemctl(action: str, service_name: list) -> None:
    subprocess.run(["systemctl", action, *service_name]).check_returncode()


def service_start(service_name: list) -> None:
    _systemctl("start", service_name)


def service_stop(service_name: list) -> None:
    _systemctl("stop", service_name)


def service_restart(service_name: list) -> None:
    _systemctl("restart", service_name)


def service_enable(service_name: list) -> None:
    _systemctl("enable", service_name)


def change_directory_permissions(path, mode):
    for path_root, dirs, files in os.walk(path, topdown=False):
        for directory in [os.path.join(path_root, d) for d in dirs]:
            os.chmod(directory, mode)
        for file in [os.path.join(path_root, f) for f in files]:
            os.chmod(file, mode)


def extract_file(path, to_directory) -> None:
    try:
        file = None
        if path.endswith(".tar.gz"):
            opener, mode = tarfile.open, "r:gz"
            cwd = os.getcwd()
            os.chdir(to_directory)
            file = opener(path, mode)
            file.extractall()
    finally:
        if file:
            file.close()
        os.chdir(cwd)


def render_template(template_file, destination_file, data: dict, mode) -> None:
    with open(template_file, "r", encoding="utf-8") as source_temp:
        content = Template(source_temp.read()).render(data)
        with open(destination_file, "w", encoding="utf-8") as rendered_file:
            rendered_file.write(content)
    os.chmod(destination_file, mode)


def copy_files(origin: dict, destination: dict, mode) -> None:
    for file, origin_path in origin.items():
        destination_path = destination[file]
        shutil.copy(origin_path, destination_path)
        os.chmod(destination_path, mode)
