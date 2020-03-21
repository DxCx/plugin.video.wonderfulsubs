import requests

from .constants import API_BASE, BASE_URL
from .ui import control


def login():
    """Log in to wonderful subs and store retrieved token in the settings.

    :return: retrieved token
    """
    username = control.getSetting("login.name")
    password = control.getSetting("login.password")

    if not (username and password):
        control.ok_dialog(control.lang(30400), control.lang(30401))
        return

    url = "{}/{}/users/login".format(BASE_URL, API_BASE)
    payload = {"username": username, "password": password}
    data = requests.post(url, json=payload).json()

    if data["success"] is not True:
        control.ok_dialog(control.lang(30400), control.lang(30401))
        return

    token = data["token"]
    control.setSetting("login.token", token)
    return token


def logout():
    """Logout from wonderful subs."""
    control.setSetting("login.token", None)
