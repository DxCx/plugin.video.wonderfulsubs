from .login import login, logout
from .ui.router import route


@route('wonderful_login')
def wonderful_login(payload, params):
    return login()


@route('wonderful_logout')
def wonderful_login(payload, params):
    return logout()
