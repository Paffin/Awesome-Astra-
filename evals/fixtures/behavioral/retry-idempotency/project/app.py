from payments import transfer


def deliver(path, event_id, source, destination, cents, fail_after_debit=False):
    return transfer(path, event_id, source, destination, cents, fail_after_debit)
