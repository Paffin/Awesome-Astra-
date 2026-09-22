from pricing import total

def checkout(subtotal_cents, member=False):
    return {'total_cents': total(subtotal_cents, member)}
