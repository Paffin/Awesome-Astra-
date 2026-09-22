from store import migrate, read_account


def start(path):
    migrate(path)


def account(path, account_id):
    return read_account(path, account_id)
